use numpy::PyReadonlyArray3;
use pyo3::prelude::*;
use pyo3::types::PyString;
use std::cell::RefCell;

/// Precomputed decimal strings for all `u8` values (0..=255).
/// Eliminates integer division/modulo in the ANSI formatting hot loop.
const U8_DEC: [&str; 256] = [
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
    "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    "30", "31", "32", "33", "34", "35", "36", "37", "38", "39",
    "40", "41", "42", "43", "44", "45", "46", "47", "48", "49",
    "50", "51", "52", "53", "54", "55", "56", "57", "58", "59",
    "60", "61", "62", "63", "64", "65", "66", "67", "68", "69",
    "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
    "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
    "90", "91", "92", "93", "94", "95", "96", "97", "98", "99",
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
    "110", "111", "112", "113", "114", "115", "116", "117", "118", "119",
    "120", "121", "122", "123", "124", "125", "126", "127", "128", "129",
    "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
    "140", "141", "142", "143", "144", "145", "146", "147", "148", "149",
    "150", "151", "152", "153", "154", "155", "156", "157", "158", "159",
    "160", "161", "162", "163", "164", "165", "166", "167", "168", "169",
    "170", "171", "172", "173", "174", "175", "176", "177", "178", "179",
    "180", "181", "182", "183", "184", "185", "186", "187", "188", "189",
    "190", "191", "192", "193", "194", "195", "196", "197", "198", "199",
    "200", "201", "202", "203", "204", "205", "206", "207", "208", "209",
    "210", "211", "212", "213", "214", "215", "216", "217", "218", "219",
    "220", "221", "222", "223", "224", "225", "226", "227", "228", "229",
    "230", "231", "232", "233", "234", "235", "236", "237", "238", "239",
    "240", "241", "242", "243", "244", "245", "246", "247", "248", "249",
    "250", "251", "252", "253", "254", "255",
];

thread_local! {
    /// Reused on each render call on a given Python worker thread.
    ///
    /// The returned Python `str` is immutable and therefore still requires a
    /// Python-side allocation, but reusing this Rust buffer avoids rebuilding
    /// the large native `String` capacity for every video frame.
    static OUTPUT_BUFFER: RefCell<String> = RefCell::new(String::new());
}

#[inline]
fn validate_charset(charset: &[String]) -> PyResult<()> {
    if charset.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Charset must be a non-empty string.",
        ));
    }

    Ok(())
}

/// Build a 256-entry integer lookup table for pixel intensity -> charset index.
///
/// This replaces a floating-point multiply and conversion for every pixel.
/// For the small charset sizes supported by Asciify, integer division gives
/// the same floor mapping as `(value as f32 * scale) as usize`.
#[inline]
fn build_charset_lut(charset_len: usize) -> [usize; 256] {
    let max_idx = charset_len - 1;
    let mut lut = [0usize; 256];

    for (value, slot) in lut.iter_mut().enumerate() {
        *slot = value * max_idx / 255;
    }

    lut
}

#[inline]
fn max_charset_byte_len(charset: &[String]) -> usize {
    charset.iter().map(String::len).max().unwrap_or(1)
}

/// Reserve enough room for the common case so the render buffer does not
/// repeatedly grow while appending ANSI sequences.
#[inline]
fn color_buffer_capacity(rows: usize, cols: usize, max_char_len: usize) -> usize {
    // Prefix: "\x1b[38;2;" = 7 bytes
    // RGB digits + two separators: at most 11 bytes
    // "m" = 1 byte
    // character + "." + "\x1b[0m" = max_char_len + 5 bytes
    // Total per pixel: max_char_len + 24 bytes, plus row newlines.
    rows.saturating_mul(
        cols.saturating_mul(max_char_len.saturating_add(24)),
    )
    .saturating_add(rows)
}

#[inline]
fn grayscale_buffer_capacity(rows: usize, cols: usize, max_char_len: usize) -> usize {
    rows.saturating_mul(
        cols.saturating_mul(max_char_len.saturating_add(1)),
    )
    .saturating_add(rows)
}

#[inline]
fn fill_buffer_capacity(rows: usize, cols: usize) -> usize {
    // Worst-case per pixel: "\x1b[48;2;255;255;255m  " (21 bytes),
    // plus "\x1b[0m\n" (5 bytes) once per row.
    rows.saturating_mul(cols.saturating_mul(21).saturating_add(5))
}

#[inline]
fn fill_hd_buffer_capacity(rows: usize, cols: usize) -> usize {
    // Two input rows pack into one terminal line.
    // Worst-case per cell: "\x1b[38;2;255;255;255;48;2;255;255;255m▀" (39 bytes),
    // plus "\x1b[0m\n" (5 bytes) once per output line.
    let out_rows = rows.div_ceil(2);
    out_rows.saturating_mul(cols.saturating_mul(39).saturating_add(5))
}

/// Reuse the per-thread Rust output buffer, then copy the finished UTF-8
/// string into one Python `str`.
fn with_reused_output_buffer<'py, F>(
    py: Python<'py>,
    capacity: usize,
    render: F,
) -> PyResult<Py<PyString>>
where
    F: FnOnce(&mut String) -> PyResult<()>,
{
    OUTPUT_BUFFER.with(|buffer| {
        let mut output = buffer.borrow_mut();
        output.clear();

        let current_capacity = output.capacity();
        if current_capacity < capacity {
            output.reserve(capacity - current_capacity);
        }

        render(&mut output)?;

        Ok(PyString::new(py, output.as_str()).unbind())
    })
}

/// Append a u8 decimal string via a branchless 256-entry lookup table.
#[inline(always)]
fn push_u8_decimal(output: &mut String, value: u8) {
    output.push_str(U8_DEC[value as usize]);
}

#[inline(always)]
fn push_rgb_params(output: &mut String, r: u8, g: u8, b: u8) {
    push_u8_decimal(output, r);
    output.push(';');
    push_u8_decimal(output, g);
    output.push(';');
    push_u8_decimal(output, b);
}

#[inline(always)]
fn render_color_pixel(
    output: &mut String,
    r_val: u8,
    g_val: u8,
    b_val: u8,
    charset: &[String],
    charset_lut: &[usize; 256],
) {
    let max_val = r_val.max(g_val).max(b_val);
    let safe_idx = charset_lut[max_val as usize];

    output.push_str("\x1b[38;2;");
    push_rgb_params(output, r_val, g_val, b_val);
    output.push('m');
    output.push_str(&charset[safe_idx]);
    output.push('.');
    output.push_str("\x1b[0m");
}

#[inline(always)]
fn push_fill_pixel(
    output: &mut String,
    rgb: (u8, u8, u8),
    prev_bg: &mut Option<(u8, u8, u8)>,
) {
    if *prev_bg != Some(rgb) {
        output.push_str("\x1b[48;2;");
        push_rgb_params(output, rgb.0, rgb.1, rgb.2);
        output.push('m');
        *prev_bg = Some(rgb);
    }
    output.push_str("  ");
}

#[inline(always)]
fn push_fill_hd_cell(
    output: &mut String,
    top: (u8, u8, u8),
    bot: (u8, u8, u8),
    prev_fg: &mut Option<(u8, u8, u8)>,
    prev_bg: &mut Option<(u8, u8, u8)>,
) {
    // When top and bottom pixels match, a single background-colored space
    // fills the full cell with zero transparent area and avoids updating fg.
    if top == bot {
        if *prev_bg != Some(top) {
            output.push_str("\x1b[48;2;");
            push_rgb_params(output, top.0, top.1, top.2);
            output.push('m');
            *prev_bg = Some(top);
        }
        output.push(' ');
        return;
    }

    let fg_changed = *prev_fg != Some(top);
    let bg_changed = *prev_bg != Some(bot);

    match (fg_changed, bg_changed) {
        (true, true) => {
            output.push_str("\x1b[38;2;");
            push_rgb_params(output, top.0, top.1, top.2);
            output.push_str(";48;2;");
            push_rgb_params(output, bot.0, bot.1, bot.2);
            output.push('m');
            *prev_fg = Some(top);
            *prev_bg = Some(bot);
        }
        (true, false) => {
            output.push_str("\x1b[38;2;");
            push_rgb_params(output, top.0, top.1, top.2);
            output.push('m');
            *prev_fg = Some(top);
        }
        (false, true) => {
            output.push_str("\x1b[48;2;");
            push_rgb_params(output, bot.0, bot.1, bot.2);
            output.push('m');
            *prev_bg = Some(bot);
        }
        (false, false) => {}
    }

    // Upper half-block: foreground fills top half, background fills bottom half.
    output.push('▀');
}

/// Render a contiguous RGB/BGR array without ndarray index lookups.
///
/// NumPy arrays produced by PIL/OpenCV are normally C-contiguous. Keeping a
/// strided fallback below preserves compatibility with arbitrary NumPy views.
fn render_color_contiguous(
    output: &mut String,
    data: &[u8],
    rows: usize,
    cols: usize,
    channels: usize,
    charset: &[String],
    charset_lut: &[usize; 256],
) {
    if cols == 0 {
        for _ in 0..rows {
            output.push('\n');
        }
        return;
    }

    let row_len = cols * channels;

    for row in data.chunks_exact(row_len).take(rows) {
        for pixel in row.chunks_exact(channels).take(cols) {
            render_color_pixel(
                output,
                pixel[0],
                pixel[1],
                pixel[2],
                charset,
                charset_lut,
            );
        }
        output.push('\n');
    }
}

fn render_fill_contiguous(
    output: &mut String,
    data: &[u8],
    rows: usize,
    cols: usize,
    channels: usize,
) {
    if cols == 0 {
        for _ in 0..rows {
            output.push('\n');
        }
        return;
    }

    let row_len = cols * channels;

    for row in data.chunks_exact(row_len).take(rows) {
        let mut prev_bg: Option<(u8, u8, u8)> = None;
        for pixel in row.chunks_exact(channels).take(cols) {
            push_fill_pixel(output, (pixel[0], pixel[1], pixel[2]), &mut prev_bg);
        }
        output.push_str("\x1b[0m\n");
    }
}

fn render_fill_hd_contiguous(
    output: &mut String,
    data: &[u8],
    rows: usize,
    cols: usize,
    channels: usize,
) {
    if cols == 0 {
        for _ in 0..rows.div_ceil(2) {
            output.push('\n');
        }
        return;
    }

    let row_len = cols * channels;
    let mut r = 0;

    while r < rows {
        let top_start = r * row_len;
        let top_row = &data[top_start..top_start + row_len];
        let bot_row = if r + 1 < rows {
            let bot_start = (r + 1) * row_len;
            &data[bot_start..bot_start + row_len]
        } else {
            // Odd height: mirror final row so the bottom half is also filled.
            top_row
        };

        let mut prev_fg: Option<(u8, u8, u8)> = None;
        let mut prev_bg: Option<(u8, u8, u8)> = None;

        for (top_px, bot_px) in top_row
            .chunks_exact(channels)
            .zip(bot_row.chunks_exact(channels))
            .take(cols)
        {
            push_fill_hd_cell(
                output,
                (top_px[0], top_px[1], top_px[2]),
                (bot_px[0], bot_px[1], bot_px[2]),
                &mut prev_fg,
                &mut prev_bg,
            );
        }

        output.push_str("\x1b[0m\n");
        r += 2;
    }
}

/// Target A: Converts a generic RGB image array into the Grid structure.
/// Returns: List[List[(char, (r, g, b))]]
#[pyfunction]
fn image_to_ascii_rs(
    img_array: PyReadonlyArray3<u8>,
    charset: Vec<String>,
) -> PyResult<Vec<Vec<(String, (u8, u8, u8))>>> {
    validate_charset(&charset)?;

    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];
    let channels = shape[2];
    let lut = build_charset_lut(charset.len());

    let mut grid = Vec::with_capacity(rows);

    if let Some(data) = array.as_slice() {
        if channels >= 3 && cols > 0 {
            let row_len = cols * channels;

            for row in data.chunks_exact(row_len).take(rows) {
                let mut row_data = Vec::with_capacity(cols);

                for pixel in row.chunks_exact(channels).take(cols) {
                    let r_val = pixel[0];
                    let g_val = pixel[1];
                    let b_val = pixel[2];
                    let max_val = r_val.max(g_val).max(b_val);
                    let safe_idx = lut[max_val as usize];

                    row_data.push((
                        charset[safe_idx].clone(),
                        (r_val, g_val, b_val),
                    ));
                }

                grid.push(row_data);
            }

            return Ok(grid);
        }
    }

    // Compatibility path for non-contiguous arrays or arrays with fewer than
    // three channels. This preserves the old out-of-bounds -> zero behavior.
    for r in 0..rows {
        let mut row_data = Vec::with_capacity(cols);

        for c in 0..cols {
            let r_val = *array.get([r, c, 0]).unwrap_or(&0);
            let g_val = *array.get([r, c, 1]).unwrap_or(&0);
            let b_val = *array.get([r, c, 2]).unwrap_or(&0);
            let max_val = r_val.max(g_val).max(b_val);
            let safe_idx = lut[max_val as usize];

            row_data.push((
                charset[safe_idx].clone(),
                (r_val, g_val, b_val),
            ));
        }

        grid.push(row_data);
    }

    Ok(grid)
}

/// Target B: Renders an entire frame directly to a single ANSI string.
#[pyfunction]
fn render_frame_to_string(
    py: Python,
    img_array: PyReadonlyArray3<u8>,
    charset: Vec<String>,
) -> PyResult<Py<PyString>> {
    validate_charset(&charset)?;

    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];
    let channels = shape[2];
    let charset_lut = build_charset_lut(charset.len());
    let capacity = color_buffer_capacity(rows, cols, max_charset_byte_len(&charset));

    with_reused_output_buffer(py, capacity, |output| {
        if let Some(data) = array.as_slice() {
            if channels >= 3 {
                render_color_contiguous(
                    output,
                    data,
                    rows,
                    cols,
                    channels,
                    &charset,
                    &charset_lut,
                );
                return Ok(());
            }
        }

        // Compatibility path for non-contiguous arrays or arrays with fewer
        // than three channels. Keep the previous zero-fallback semantics.
        for r in 0..rows {
            for c in 0..cols {
                let r_val = *array.get([r, c, 0]).unwrap_or(&0);
                let g_val = *array.get([r, c, 1]).unwrap_or(&0);
                let b_val = *array.get([r, c, 2]).unwrap_or(&0);

                render_color_pixel(
                    output,
                    r_val,
                    g_val,
                    b_val,
                    &charset,
                    &charset_lut,
                );
            }
            output.push('\n');
        }

        Ok(())
    })
}

/// Render a contiguous grayscale frame directly to the shared output buffer.
fn render_grayscale_contiguous(
    output: &mut String,
    data: &[u8],
    rows: usize,
    cols: usize,
    channels: usize,
    charset: &[String],
    charset_lut: &[usize; 256],
) {
    if cols == 0 {
        for _ in 0..rows {
            output.push('\n');
        }
        return;
    }

    let row_len = cols * channels;

    for row in data.chunks_exact(row_len).take(rows) {
        for pixel in row.chunks_exact(channels).take(cols) {
            let max_val = pixel[0].max(pixel[1]).max(pixel[2]);
            let safe_idx = charset_lut[max_val as usize];
            output.push_str(&charset[safe_idx]);
            output.push(' ');
        }
        output.push('\n');
    }
}

/// Target C: Renders a grayscale frame directly to a single ASCII string.
///
/// Grayscale conversion uses the maximum of the first three channels, which
/// matches the Python converter and is invariant to RGB/BGR channel order.
#[pyfunction]
fn render_grayscale_to_string(
    py: Python,
    img_array: PyReadonlyArray3<u8>,
    charset: Vec<String>,
) -> PyResult<Py<PyString>> {
    validate_charset(&charset)?;

    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];
    let channels = shape[2];
    let charset_lut = build_charset_lut(charset.len());
    let capacity =
        grayscale_buffer_capacity(rows, cols, max_charset_byte_len(&charset));

    with_reused_output_buffer(py, capacity, |output| {
        if let Some(data) = array.as_slice() {
            if channels >= 3 {
                render_grayscale_contiguous(
                    output,
                    data,
                    rows,
                    cols,
                    channels,
                    &charset,
                    &charset_lut,
                );
                return Ok(());
            }
        }

        // Compatibility path for non-contiguous arrays or arrays with fewer
        // than three channels. Keep the previous zero-fallback semantics.
        for r in 0..rows {
            for c in 0..cols {
                let c0 = *array.get([r, c, 0]).unwrap_or(&0);
                let c1 = *array.get([r, c, 1]).unwrap_or(&0);
                let c2 = *array.get([r, c, 2]).unwrap_or(&0);

                let max_val = c0.max(c1).max(c2);
                let safe_idx = charset_lut[max_val as usize];
                output.push_str(&charset[safe_idx]);
                output.push(' ');
            }
            output.push('\n');
        }

        Ok(())
    })
}

/// Target D: Renders a solid full-fill frame using 24-bit background ANSI codes
/// (`\x1b[48;2;R;G;Bm  `) with run-length color deduplication and a single reset
/// per line, leaving zero transparent space.
#[pyfunction]
fn render_fill_to_string(
    py: Python,
    img_array: PyReadonlyArray3<u8>,
) -> PyResult<Py<PyString>> {
    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];
    let channels = shape[2];
    let capacity = fill_buffer_capacity(rows, cols);

    with_reused_output_buffer(py, capacity, |output| {
        if let Some(data) = array.as_slice() {
            if channels >= 3 {
                render_fill_contiguous(output, data, rows, cols, channels);
                return Ok(());
            }
        }

        for r in 0..rows {
            let mut prev_bg: Option<(u8, u8, u8)> = None;
            for c in 0..cols {
                let r_val = *array.get([r, c, 0]).unwrap_or(&0);
                let g_val = *array.get([r, c, 1]).unwrap_or(&0);
                let b_val = *array.get([r, c, 2]).unwrap_or(&0);
                push_fill_pixel(output, (r_val, g_val, b_val), &mut prev_bg);
            }
            if cols > 0 {
                output.push_str("\x1b[0m\n");
            } else {
                output.push('\n');
            }
        }

        Ok(())
    })
}

/// Target E: Renders a high-density full-fill frame using Unicode upper
/// half-blocks (`▀`) where foreground is the top pixel and background is the
/// bottom pixel, doubling vertical and horizontal terminal density with zero
/// transparent space.
#[pyfunction]
fn render_fill_hd_to_string(
    py: Python,
    img_array: PyReadonlyArray3<u8>,
) -> PyResult<Py<PyString>> {
    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];
    let channels = shape[2];
    let capacity = fill_hd_buffer_capacity(rows, cols);

    with_reused_output_buffer(py, capacity, |output| {
        if let Some(data) = array.as_slice() {
            if channels >= 3 {
                render_fill_hd_contiguous(output, data, rows, cols, channels);
                return Ok(());
            }
        }

        let mut r = 0;
        while r < rows {
            let bot_r = if r + 1 < rows { r + 1 } else { r };
            let mut prev_fg: Option<(u8, u8, u8)> = None;
            let mut prev_bg: Option<(u8, u8, u8)> = None;

            for c in 0..cols {
                let top = (
                    *array.get([r, c, 0]).unwrap_or(&0),
                    *array.get([r, c, 1]).unwrap_or(&0),
                    *array.get([r, c, 2]).unwrap_or(&0),
                );
                let bot = (
                    *array.get([bot_r, c, 0]).unwrap_or(&0),
                    *array.get([bot_r, c, 1]).unwrap_or(&0),
                    *array.get([bot_r, c, 2]).unwrap_or(&0),
                );
                push_fill_hd_cell(output, top, bot, &mut prev_fg, &mut prev_bg);
            }

            if cols > 0 {
                output.push_str("\x1b[0m\n");
            } else {
                output.push('\n');
            }
            r += 2;
        }

        Ok(())
    })
}

#[pymodule]
fn ascii_art_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(image_to_ascii_rs, m)?)?;
    m.add_function(wrap_pyfunction!(render_frame_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(render_grayscale_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(render_fill_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(render_fill_hd_to_string, m)?)?;
    Ok(())
}

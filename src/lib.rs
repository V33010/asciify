use numpy::PyReadonlyArray3;
use pyo3::prelude::*;
use pyo3::types::PyString;
use std::cell::RefCell;

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

        Ok(PyString::new_bound(py, output.as_str()).unbind())
    })
}

/// Append a u8 without invoking the formatting machinery.
///
/// The color renderer performs this three times per pixel, so avoiding
/// `write!`/`Display` formatting keeps the hot loop allocation-free.
#[inline(always)]
fn push_u8_decimal(output: &mut String, value: u8) {
    if value >= 100 {
        output.push((b'0' + value / 100) as char);
        output.push((b'0' + (value / 10) % 10) as char);
        output.push((b'0' + value % 10) as char);
    } else if value >= 10 {
        output.push((b'0' + value / 10) as char);
        output.push((b'0' + value % 10) as char);
    } else {
        output.push((b'0' + value) as char);
    }
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
    push_u8_decimal(output, r_val);
    output.push(';');
    push_u8_decimal(output, g_val);
    output.push(';');
    push_u8_decimal(output, b_val);
    output.push('m');
    output.push_str(&charset[safe_idx]);
    output.push('.');
    output.push_str("\x1b[0m");
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

/// Target A: Converts a generic RGB image array into the Grid structure.
/// Returns: List[List[(char, (r, g, b))]]
#[pyfunction]
fn image_to_ascii_rs(
    _py: Python,
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
///
/// Phase 5 optimizations:
/// - contiguous slice traversal for normal NumPy arrays;
/// - 256-entry intensity -> charset LUT;
/// - manual u8 formatting instead of `write!`;
/// - per-thread output-buffer reuse.
///
/// Parallelism/SIMD is intentionally not added here: the benchmarked output
/// sizes are small, and the hot path is dominated by ordered ANSI string
/// production. Those techniques should only be introduced if profiling shows
/// they remain material after these simpler optimizations.
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

#[pymodule]
fn ascii_art_rs(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(image_to_ascii_rs, m)?)?;
    m.add_function(wrap_pyfunction!(render_frame_to_string, m)?)?;
    m.add_function(wrap_pyfunction!(render_grayscale_to_string, m)?)?;
    Ok(())
}

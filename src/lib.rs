use numpy::PyReadonlyArray3;
use pyo3::prelude::*;
use std::fmt::Write; // Needed to write into the string buffer efficiently

/// Target A: Converts a generic RGB image array into the Grid structure
/// Returns: List[List[(char, (r, g, b))]]
#[pyfunction]
fn image_to_ascii_rs(
    _py: Python,
    img_array: PyReadonlyArray3<u8>,
    charset: Vec<String>,
) -> PyResult<Vec<Vec<(String, (u8, u8, u8))>>> {
    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];

    let max_idx = (charset.len() - 1) as f32;
    let scale = max_idx / 255.0;

    let mut grid = Vec::with_capacity(rows);

    for r in 0..rows {
        let mut row_data = Vec::with_capacity(cols);
        for c in 0..cols {
            let pixel = (
                *array.get([r, c, 0]).unwrap_or(&0),
                *array.get([r, c, 1]).unwrap_or(&0),
                *array.get([r, c, 2]).unwrap_or(&0),
            );

            let max_val = pixel.0.max(pixel.1).max(pixel.2);
            let idx = (max_val as f32 * scale) as usize;
            let safe_idx = idx.min(charset.len() - 1);
            let char_str = &charset[safe_idx];

            row_data.push((char_str.clone(), pixel));
        }
        grid.push(row_data);
    }

    Ok(grid)
}

/// Target B: Renders an entire frame directly to a single ANSI string.
/// Eliminates thousands of Python string allocations per frame.
#[pyfunction]
fn render_frame_to_string(
    _py: Python,
    img_array: PyReadonlyArray3<u8>,
    charset: Vec<String>,
) -> PyResult<String> {
    let array = img_array.as_array();
    let shape = array.shape();
    let rows = shape[0];
    let cols = shape[1];

    // Estimate buffer size to avoid reallocations.
    // Each pixel needs approx 20-25 bytes for ANSI codes: "\x1b[38;2;255;255;255mX\x1b[0m"
    // + newlines.
    let capacity = rows * cols * 25 + rows;
    let mut output = String::with_capacity(capacity);

    let max_idx = (charset.len() - 1) as f32;
    let scale = max_idx / 255.0;

    for r in 0..rows {
        for c in 0..cols {
            let r_val = *array.get([r, c, 0]).unwrap_or(&0);
            let g_val = *array.get([r, c, 1]).unwrap_or(&0);
            let b_val = *array.get([r, c, 2]).unwrap_or(&0);

            // 1. Calculate Char
            let max_val = r_val.max(g_val).max(b_val);
            let idx = (max_val as f32 * scale) as usize;
            let safe_idx = idx.min(charset.len() - 1);
            let char_str = &charset[safe_idx];

            // 2. Write ANSI directly to buffer
            // Format: \x1b[38;2;R;G;BmCHAR.\x1b[0m
            // We append a dot '.' after the char for aspect ratio correction (same as your Python code)
            write!(
                output,
                "\x1b[38;2;{};{};{}m{}.\x1b[0m",
                r_val, g_val, b_val, char_str
            )
            .unwrap();
        }
        // End of row
        output.push('\n');
    }

    Ok(output)
}

#[pymodule]
fn ascii_art_rs(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(image_to_ascii_rs, m)?)?;
    m.add_function(wrap_pyfunction!(render_frame_to_string, m)?)?;
    Ok(())
}

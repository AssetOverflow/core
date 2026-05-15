//! core-rs: Rust extension for CORE-AI
//!
//! Exposes hot-path operations to Python via PyO3:
//!   - geometric_product   (Cl(4,1) full product via precomputed table)
//!   - versor_apply        (sandwich product V*F*rev(V))
//!   - versor_condition    (||F*rev(F) - 1||_F)
//!   - cga_inner           (symmetric inner product)
//!   - vault_recall        (parallel top-k scan)
//!
//! All multivectors are f32 arrays of length 32, passed as numpy arrays.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

pub mod cga;
pub mod cl41;
pub mod vault;
pub mod versor;

use cga::cga_inner_raw;
use cl41::geometric_product_raw;
use vault::vault_recall_raw;
use versor::{normalize_to_versor_raw, versor_apply_closed, versor_apply_raw, versor_condition_raw};

/// Geometric product in Cl(4,1). Accepts two numpy-compatible f32 arrays of length 32.
#[pyfunction]
fn geometric_product(
    py: Python<'_>,
    a: &pyo3::types::PyAny,
    b: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let a_slice = extract_f32_slice(a)?;
    let b_slice = extract_f32_slice(b)?;
    let result = geometric_product_raw(&a_slice, &b_slice)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    f32_array_to_numpy(py, &result)
}

/// Sandwich product V*F*reverse(V).
#[pyfunction]
fn versor_apply(
    py: Python<'_>,
    v: &pyo3::types::PyAny,
    f: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let v_slice = extract_f32_slice(v)?;
    let f_slice = extract_f32_slice(f)?;
    let result = versor_apply_raw(&v_slice, &f_slice)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    f32_array_to_numpy(py, &result)
}

/// Sandwich product V*F*reverse(V) with closure semantics.
/// Preserves null vectors, applies unit-versor closure with seed fallback.
#[pyfunction]
fn versor_apply_with_closure(
    py: Python<'_>,
    v: &pyo3::types::PyAny,
    f: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let v_slice = extract_f32_slice(v)?;
    let f_slice = extract_f32_slice(f)?;
    let result = versor_apply_closed(&v_slice, &f_slice)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    f32_array_to_numpy(py, &result)
}

/// ||F*reverse(F) - 1||_F. Returns scalar f32.
#[pyfunction]
fn versor_condition(f: &pyo3::types::PyAny) -> PyResult<f32> {
    let f_slice = extract_f32_slice(f)?;
    versor_condition_raw(&f_slice).map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Project F onto versor manifold: F / sqrt(|F*rev(F)|).
#[pyfunction]
fn normalize_to_versor(
    py: Python<'_>,
    f: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let f_slice = extract_f32_slice(f)?;
    let result = normalize_to_versor_raw(&f_slice)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    f32_array_to_numpy(py, &result)
}

/// Symmetric CGA inner product: 0.5 * scalar(X*Y + Y*X).
#[pyfunction]
fn cga_inner(x: &pyo3::types::PyAny, y: &pyo3::types::PyAny) -> PyResult<f32> {
    let x_slice = extract_f32_slice(x)?;
    let y_slice = extract_f32_slice(y)?;
    cga_inner_raw(&x_slice, &y_slice).map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Parallel top-k vault recall by CGA inner product.
#[pyfunction]
fn vault_recall(
    versors: Vec<&pyo3::types::PyAny>,
    query: &pyo3::types::PyAny,
    top_k: usize,
) -> PyResult<Vec<(usize, f32)>> {
    let query_slice = extract_f32_slice(query)?;
    let mut slices: Vec<[f32; 32]> = Vec::with_capacity(versors.len());
    for v in &versors {
        slices.push(extract_f32_slice(v)?);
    }
    vault_recall_raw(&slices, &query_slice, top_k)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

fn extract_f32_slice(obj: &pyo3::types::PyAny) -> PyResult<[f32; 32]> {
    let np = obj.py().import("numpy")?;
    let arr = np.call_method1("asarray", (obj, "float32"))?;
    let flat = arr.call_method0("flatten")?;
    let list: Vec<f32> = flat.extract()?;
    if list.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "Expected array of length 32, got {}",
            list.len()
        )));
    }
    let mut out = [0f32; 32];
    out.copy_from_slice(&list);
    Ok(out)
}

fn f32_array_to_numpy(py: Python<'_>, data: &[f32; 32]) -> PyResult<PyObject> {
    let np = py.import("numpy")?;
    let list: Vec<f32> = data.to_vec();
    let arr = np.call_method1("array", (list, "float32"))?;
    Ok(arr.into_py(py))
}

#[pymodule]
fn core_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(geometric_product, m)?)?;
    m.add_function(wrap_pyfunction!(versor_apply, m)?)?;
    m.add_function(wrap_pyfunction!(versor_apply_with_closure, m)?)?;
    m.add_function(wrap_pyfunction!(versor_condition, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_to_versor, m)?)?;
    m.add_function(wrap_pyfunction!(cga_inner, m)?)?;
    m.add_function(wrap_pyfunction!(vault_recall, m)?)?;
    Ok(())
}

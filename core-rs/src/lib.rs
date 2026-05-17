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
pub mod diffusion;
pub mod vault;
pub mod versor;

use cga::cga_inner_raw;
use cl41::geometric_product_raw;
use diffusion::{graph_diffusion_step, unitize_f32};
#[allow(unused_imports)]
use vault::vault_recall_raw;
use versor::{
    normalize_to_versor_raw, versor_apply_closed, versor_apply_closed_f64, versor_apply_raw,
    versor_condition_raw,
};

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

/// `versor_apply` f64 closure path — bit-identity port of Python
/// `algebra.versor.versor_apply` + `_close_applied_versor`.
/// Inputs and output are float64.  ADR-0020 parity surface.
#[pyfunction]
fn versor_apply_with_closure_f64(
    py: Python<'_>,
    v: &pyo3::types::PyAny,
    f: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let v_slice = extract_f64_slice(v)?;
    let f_slice = extract_f64_slice(f)?;
    let result = versor_apply_closed_f64(&v_slice, &f_slice)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    f64_array_to_numpy(py, &result)
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

/// Parallel top-k vault recall by CGA inner product (zero-copy).
///
/// Per ADR-0020 follow-on (task #35): accepts a 2D numpy
/// (N, 32) float32 array via `PyReadonlyArray2`, which exposes a
/// view *directly into the numpy buffer*.  No Python→Rust copy,
/// no re-chunking — Rayon scores straight off the source slice.
/// This is the load-bearing reason for the Rust path: NumPy
/// already SIMD-vectorises the same kernel; the only win Rust
/// can offer is *avoiding the marshalling tax* and adding
/// thread-parallel scoring on top.
#[pyfunction]
fn vault_recall(
    versors: numpy::PyReadonlyArray2<'_, f32>,
    query: numpy::PyReadonlyArray1<'_, f32>,
    top_k: usize,
) -> PyResult<Vec<(usize, f32)>> {
    let view = versors.as_array();
    let shape = view.shape();
    if shape.len() != 2 || shape[1] != 32 {
        return Err(PyValueError::new_err(format!(
            "versors must be shape (N, 32), got {:?}",
            shape
        )));
    }
    let n = shape[0];
    let q_slice = query.as_slice().map_err(|e| {
        PyValueError::new_err(format!("query must be contiguous f32 (32,): {}", e))
    })?;
    if q_slice.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "query must have length 32, got {}",
            q_slice.len()
        )));
    }
    let v_slice = versors.as_slice().map_err(|e| {
        PyValueError::new_err(format!(
            "versors must be C-contiguous f32 (N, 32): {}",
            e
        ))
    })?;
    let mut q_arr = [0f32; 32];
    q_arr.copy_from_slice(q_slice);

    crate::vault::vault_recall_flat(v_slice, n, &q_arr, top_k)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

/// Unitize a multivector via the Cl(4,1) exponential map.
/// Distinguishes boost planes (cosh/sinh) from rotation planes (cos/sin).
#[pyfunction]
fn unitize_expmap(
    py: Python<'_>,
    v: &pyo3::types::PyAny,
) -> PyResult<PyObject> {
    let v_slice = extract_f32_slice(v)?;
    let result = unitize_f32(&v_slice);
    f32_array_to_numpy(py, &result)
}

/// One forward step of graph diffusion.
/// Takes fields (N x 32 flat), edges (E x 2 flat), damping.
/// Returns (new_fields_flat, delta).
#[pyfunction]
fn diffusion_step(
    py: Python<'_>,
    fields_flat: Vec<f32>,
    edges_flat: Vec<i32>,
    n_nodes: usize,
    damping: f64,
) -> PyResult<(PyObject, f64)> {
    if fields_flat.len() != n_nodes * 32 {
        return Err(PyValueError::new_err(format!(
            "fields_flat length {} != n_nodes * 32 = {}",
            fields_flat.len(), n_nodes * 32,
        )));
    }

    let mut fields: Vec<[f32; 32]> = Vec::with_capacity(n_nodes);
    for i in 0..n_nodes {
        let mut arr = [0f32; 32];
        arr.copy_from_slice(&fields_flat[i * 32..(i + 1) * 32]);
        fields.push(arr);
    }

    let n_edges = edges_flat.len() / 2;
    let mut edges: Vec<[i32; 2]> = Vec::with_capacity(n_edges);
    for i in 0..n_edges {
        edges.push([edges_flat[i * 2], edges_flat[i * 2 + 1]]);
    }

    let (new_fields, delta) = graph_diffusion_step(&fields, &edges, damping);

    let flat: Vec<f32> = new_fields.into_iter().flat_map(|a| a.into_iter()).collect();
    let np = py.import("numpy")?;
    let arr = np.call_method1("array", (flat, "float32"))?;
    let reshaped = arr.call_method1("reshape", ((n_nodes, 32),))?;
    Ok((reshaped.into_py(py), delta))
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

fn extract_f64_slice(obj: &pyo3::types::PyAny) -> PyResult<[f64; 32]> {
    let np = obj.py().import("numpy")?;
    let arr = np.call_method1("asarray", (obj, "float64"))?;
    let flat = arr.call_method0("flatten")?;
    let list: Vec<f64> = flat.extract()?;
    if list.len() != 32 {
        return Err(PyValueError::new_err(format!(
            "Expected array of length 32, got {}",
            list.len()
        )));
    }
    let mut out = [0f64; 32];
    out.copy_from_slice(&list);
    Ok(out)
}

fn f64_array_to_numpy(py: Python<'_>, data: &[f64; 32]) -> PyResult<PyObject> {
    let np = py.import("numpy")?;
    let list: Vec<f64> = data.to_vec();
    let arr = np.call_method1("array", (list, "float64"))?;
    Ok(arr.into_py(py))
}

#[pymodule]
fn core_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(geometric_product, m)?)?;
    m.add_function(wrap_pyfunction!(versor_apply, m)?)?;
    m.add_function(wrap_pyfunction!(versor_apply_with_closure, m)?)?;
    m.add_function(wrap_pyfunction!(versor_apply_with_closure_f64, m)?)?;
    m.add_function(wrap_pyfunction!(versor_condition, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_to_versor, m)?)?;
    m.add_function(wrap_pyfunction!(cga_inner, m)?)?;
    m.add_function(wrap_pyfunction!(vault_recall, m)?)?;
    m.add_function(wrap_pyfunction!(unitize_expmap, m)?)?;
    m.add_function(wrap_pyfunction!(diffusion_step, m)?)?;
    Ok(())
}

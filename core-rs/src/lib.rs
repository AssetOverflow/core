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
///
/// Takes ``fields`` (N x 32 float32 numpy) and ``edges`` (E x 2 int32
/// numpy) as zero-copy ``PyReadonlyArray2`` views; returns the new
/// fields as an owned ``PyArray2<f32>`` plus the scalar L2 delta.
///
/// The previous signature took ``Vec<f32>`` + ``Vec<i32>``, which forced
/// PyO3 to box-unbox every element through Python's float/int object
/// representation on the way in, and required a ``numpy.array(...)
/// .reshape(...)`` round-trip on the way out.  For a 200-step pulse
/// over a small graph this was the dominant cost — Rust-vs-Python
/// parity (0.99x) on the speedup bench was paying for marshalling,
/// not algorithm.  Zero-copy ``PyReadonlyArray2`` + ``bytemuck`` slice
/// reinterpretation removes both ends of that tax; the inner kernel
/// (``diffusion::graph_diffusion_step``) is unchanged.
#[pyfunction]
fn diffusion_step<'py>(
    py: Python<'py>,
    fields: numpy::PyReadonlyArray2<'py, f32>,
    edges: numpy::PyReadonlyArray2<'py, i32>,
    damping: f64,
) -> PyResult<(Bound<'py, numpy::PyArray2<f32>>, f64)> {
    // ``shape()`` lives on the ndarray view, not directly on
    // ``PyReadonlyArray2`` — go through ``as_array()`` to get the view.
    let fields_view = fields.as_array();
    let fields_shape = fields_view.shape();
    if fields_shape.len() != 2 || fields_shape[1] != 32 {
        return Err(PyValueError::new_err(format!(
            "fields must be shape (N, 32), got {:?}",
            fields_shape
        )));
    }
    let n_nodes = fields_shape[0];

    let edges_view = edges.as_array();
    let edges_shape = edges_view.shape();
    if edges_shape.len() != 2 || edges_shape[1] != 2 {
        return Err(PyValueError::new_err(format!(
            "edges must be shape (E, 2), got {:?}",
            edges_shape
        )));
    }

    let fields_slice = fields.as_slice().map_err(|e| {
        PyValueError::new_err(format!(
            "fields must be C-contiguous f32 (N, 32): {}",
            e
        ))
    })?;
    let edges_slice = edges.as_slice().map_err(|e| {
        PyValueError::new_err(format!(
            "edges must be C-contiguous i32 (E, 2): {}",
            e
        ))
    })?;

    // ``[f32; 32]`` and ``[i32; 2]`` are both ``Pod`` (arrays of POD
    // primitives), so reinterpretation of the contiguous numpy buffer
    // into the kernel's expected slice types is zero-copy.
    let fields_blocks: &[[f32; 32]] = bytemuck::cast_slice(fields_slice);
    let edges_blocks: &[[i32; 2]] = bytemuck::cast_slice(edges_slice);

    let (new_fields, delta) =
        graph_diffusion_step(fields_blocks, edges_blocks, damping);

    // ``Vec<[f32; 32]>`` → ``Vec<f32>`` is a zero-copy reinterpretation
    // of the allocation (requires the ``extern_crate_alloc`` bytemuck
    // feature; see Cargo.toml).
    //
    // We use ``numpy::ndarray::Array2`` (numpy 0.21's re-export of
    // ndarray 0.15) rather than ``ndarray::Array2`` to keep crate
    // versions aligned — the workspace pulls ndarray 0.16 for the
    // ``diffusion`` module but ``numpy::IntoPyArray`` is implemented
    // for ndarray 0.15's types only.
    let flat: Vec<f32> = bytemuck::allocation::cast_vec(new_fields);
    let arr = numpy::ndarray::Array2::from_shape_vec((n_nodes, 32), flat)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok((numpy::IntoPyArray::into_pyarray_bound(arr, py), delta))
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

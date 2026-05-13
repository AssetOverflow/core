// build.rs: nothing special needed for PyO3 — maturin handles the rest.
// This file exists as an extension point for future build-time codegen
// (e.g. generating the full Cl(4,1) multiplication table as a static array
// rather than computing it at OnceLock init time).
fn main() {
    println!("cargo:rerun-if-changed=src/");
}

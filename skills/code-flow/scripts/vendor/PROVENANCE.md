# Bundled Python validator

- **fastjsonschema 2.22.2**, BSD-3-Clause. [Upstream release](https://github.com/horejsek/python-fastjsonschema/tree/v2.22.2).
- Source archive: `https://github.com/horejsek/python-fastjsonschema/archive/refs/tags/v2.22.2.tar.gz`
- Archive SHA-256: `330cf64bdbf1b4c62eb10ee4a2cc85746f051c7f34065f126771c355b0981176`.
- The eleven `fastjsonschema/*.py` files are copied unchanged. The upstream license text is preserved in `fastjsonschema.LICENSE`, with CRLF line endings normalized to LF.
- Imports use the private `vendor.fastjsonschema` namespace. No package installation or network request is needed at runtime.

The maintained adapter in `../schema_validation.py` checks the supported subset of the bundled Draft 2020-12 schemas before selecting the compatible Draft 7 generator. Unknown keywords, external references and reference siblings are rejected. Defaults do not modify inputs. The adapter restores the previous Python regex semantics in each compiled function's regex table and supplies a standard-library date-time checker. Upstream files are not patched.

When updating the pinned library or schemas, run the validator regression and differential checks documented in the repository's `tests/README.md`.

# Validator regression checks

Run the maintained regression suite with Python 3.10+ and no installed packages:

```sh
python3 -E -S -B -m unittest discover -s tests -p 'test_*.py' -v
```

The suite checks schema branches, evidence/reference guards, input immutability,
error paths, regex and calendar boundaries. It copies the installable skill folders
to a temporary directory and runs behavior, atlas and paired rules generation using
`-E -S` to exclude ambient Python paths and site packages. Generated inputs and HTML
are synthetic test artifacts, not source-tracing evaluations or product templates.

To exercise a separate Skills CLI installation, set `S2S_INSTALLED_SKILLS` to its
absolute `skills` directory when running the suite. The CLI smoke test uses that
installation directly; generated artifacts still stay in its temporary workspace.

## Optional differential audit

Use a development interpreter with `jsonschema>=4.19,<5` available:

```sh
python3 -B tests/compare_validators.py
```

To compare the original upstream implementation before adapter corrections:

```sh
python3 -B tests/compare_validators.py --upstream /path/to/python-fastjsonschema-2.22.2
```

The audit mutates nested values, removes required fields and adds duplicates across
internal, render, atlas and all three layout variants. It compares acceptance and
the first error path against each original entrypoint's ordering. Unexpected
differences exit nonzero. The audit does not install packages or write reports.

Migration decisions:

- **Schema dialect:** the published schemas remain Draft 2020-12. The adapter
  accepts only the used Draft 7-compatible keywords and local `$defs` references;
  new unsupported keywords and `$ref` siblings fail at schema compilation.
- **Regex:** upstream rewrites `$` to `\Z`; the adapter preserves the previous
  Python regex behavior, including a single trailing newline where the pattern
  permits it. The original schema files are unchanged.
- **Date-time:** validation is now unconditional. A `jsonschema` installation
  without its optional format dependency previously accepted malformed timestamps.
  This intentional tightening is counted separately when that dependency is absent.
  A trailing newline accepted by the old checker's `$` regex terminator is also
  rejected and counted separately; timestamps must match the entire string.
  Valid timestamps remain accepted; dedicated regression cases cover invalid dates,
  timezone bounds, fractional seconds, lowercase `t`/`z` and rejected leap seconds.
- **Errors:** collect upstream errors, remove its synthetic `data` path prefix,
  restore integer array indices and retain the graph validator's lexicographic
  first-path ordering. Layout errors now use the same ordering; when multiple
  layout errors exist, choosing a different existing error path is counted
  separately. Message wording differs between validators.
- **Input data:** default insertion is disabled; validation preserves the supplied
  document. The integration checks for evidence, IDs, links and claims still run.

Large evaluation corpora, screenshots and generated reports remain outside the
product repository. These small checks are the maintained validator safety net.

## Migration verification

Checked on 2026-09-07 with Python 3.14.4, jsonschema 4.19.2 and the bundled
fastjsonschema 2.22.2. Each adapted comparison covered 9,454 inputs.

| Reference environment | Unexpected verdict/path differences | Intentional date-time differences | Intentional layout ordering differences |
| --- | --- | --- | --- |
| Without the optional date-time checker | 0 | 12 | 2 |
| With rfc3339-validator 0.1.4 | 0 | 3 trailing-newline timestamps | 2 |

All 16 regression tests passed, including the three CLI generation paths with site
packages disabled. The same CLI checks passed against a temporary installation
created by `npx skills add` from the local checkout. All Python sources also parsed
with Python 3.10 grammar; a Python 3.10 interpreter was not available for execution.

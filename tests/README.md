# Regression checks

Run the maintained regression suite with Python 3.10+ and no installed packages:

```sh
python3 -E -S -B -m unittest discover -s tests -p 'test_*.py' -v
```

On Windows, use `python` instead of `python3` if that is the installed command.
Neither `-X utf8` nor `PYTHONUTF8` is required; file encodings are explicit.

The suite checks schema branches, evidence/reference guards, input immutability,
error paths, regex and calendar boundaries. It copies the installable skill folders
to a temporary directory and runs behavior, atlas and paired rules generation using
`-E -S` to exclude ambient Python paths and site packages. Generated inputs and HTML
are synthetic test artifacts, not source-tracing evaluations or product templates.

`test_authored_rules.py` additionally checks version 2 picture lessons: authored
SVG and interaction packaging, transitive claim bindings, withholding all scene
assets after uncertainty/source drift, source-excerpt and fragment guards,
unchanged pair identity checks, and installed map/behavior/lesson round trips in
Korean and English under emulated cp949 file defaults. `authored_cases.py` supplies
a small explicitly synthetic cancellation policy for these tests and local visual
QA; it is not an application policy recommendation. Version 1 layouts remain
covered by the original suite. Executable presentation code still requires review;
these authoring checks do not establish a JavaScript sandbox or semantic accuracy.
Fragment regressions reject non-void HTML self-closing tags and unfinished markup
before existing pair outputs can be replaced, while retaining SVG/MathML geometry,
HTML integration points and complete comments.

`test_atlas_storage.py` checks automatic retention under the HTML directory's
`_internal/<map-stem>/`, private directory overrides, unpruned source evidence and
original layouts, and rebuilding all three layers from only the retained bundle.
It covers partial-build preservation, identity/path collisions, failed-build
immutability, source commit/evidence checks, nested Unicode filenames and installed
CLI reuse in Korean/English under emulated cp949 file defaults. Private bundles are
authoring inputs and must be excluded from shared HTML packages and web publishing.

`test_atlas_structure.py` covers the optional reviewed package/folder entries:
legacy input compatibility, Unicode containment, canonical path and reference
guards, local code/config evidence, source drift/deletion/external symlinks,
unsupported claims/owners, input immutability, and render-status integrity.
Existing installed CLI/storage checks also retain and rebuild these entries.

## Optional picture-lesson browser QA

Create the synthetic bilingual demo in a **new** directory (an existing directory
is rejected to protect its contents):

```sh
python3 -E -S -B tests/render_story_demo.py --output build/business-logic-demo
```

Open `ko/project.html` or `en/project.html` under that directory and follow the
capability to its behavior and picture lesson. For automated browser checks, use an
existing development installation of Playwright with Chromium available:

```sh
node tests/check_story_browser.cjs build/business-logic-demo /absolute/path/to/playwright
node tests/check_atlas_entry_browser.cjs build/business-logic-demo /absolute/path/to/playwright
```

The final argument is optional if Node can already resolve `playwright`. This
optional test does not install packages. It exercises both languages, desktop and
narrow-screen navigation, keyboard-operated condition controls, reset, evidence
disclosure, both themes, reduced motion, no-network rendering, JavaScript-disabled
static content, and return to the selected map/camera. Separate `runtime-*.html`
fixtures check that authored comparison classes cannot hijack shared initialization
and that legacy condition selection, theme and command-copy controls still work.
A scene with SVG/HTML `data-layer` links checks that map return state leaves local
links untouched. Scene-owned `copy-command` buttons must copy exactly once without
triggering shared announcements; missing or blank shared commands must not copy.
A deliberately incomplete legacy fixture checks that missing comparison controls
leave static cases readable and do not stop shared initialization. Screenshots go
into the demo directory for visual inspection; they are not committed. Browser
launch may need additional permission in a sandbox. Runtime generation still only
requires Python.

The same CLI checks also run with omitted text-file encodings forced to cp949 in
both the test process and every child CLI. The test-only `locale_runner.py` patches
`io.text_encoding`, `io.open` and `builtins.open`; it leaves explicit encodings,
binary I/O and standard streams unchanged. A separate check proves the emulated
default actually writes cp949 bytes and rejects an unencodable emoji. CLI checks
round-trip Korean, Japanese, Chinese and emoji text through HTML and UTF-8 render
JSON, including both `author.py` and `s2s.py --data-output` and paired rules output.
This emulates file defaults only, not all Windows behavior.

To run all in-process schema checks under the same emulated file default as well:

```sh
python3 -E -S -B tests/locale_runner.py tests/test_validation.py -v
```

To exercise a separate Skills CLI installation, set `S2S_INSTALLED_SKILLS` to its
absolute `skills` directory when running the suite. The CLI smoke test uses that
installation directly; generated artifacts still stay in its temporary workspace.

The separate entry browser check covers Korean/English at 1440, 768, 390 and
320 pixels: default overview, role/folder toggle, tree/evidence disclosure,
capability search and filters, missing-detail request copying, entry → behavior →
rules → entry state, original diagram deep links, invalid-link fallback, empty
and legacy catalogs, ungrouped components, both themes and no network requests.
The demo renderer also creates explicitly synthetic `entry-*.html` variants.
Return checks assert that the selected card is focused and inside the viewport,
both directly from behavior and through rules. Separate locale fixtures exercise
schema-accepted tags rejected by browser Intl (`en-GB-oed`, `en-foo`, `ko-foo`)
and ordinary regional tags (`en-US`, `ko-KR`) on desktop/mobile. They check that
the entry, folder tree and diagram still open without changing the IR language.
Ancestry fixtures verify actual DOM parents and expand/collapse behavior on
desktop/mobile in both languages: one-character `R`, `_` and `가` folders,
root present/omitted, children recorded before parents, an omitted intermediate
folder, and a sibling sharing a prefix (`Rextra`). Only recorded entries appear.
Use a fresh demo directory after changing templates; old HTML embeds old assets.

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

The initial migration's 16 regression tests passed, including the three CLI
generation paths with site packages disabled. The same CLI checks passed against
a temporary installation created by `npx skills add` from the local checkout.
All Python sources also parsed with Python 3.10 grammar.

### Windows encoding follow-up

The [issue #3 Windows report](https://github.com/silbaram/source-to-sight/issues/3#issuecomment-5567291520)
exercised CPython 3.10.20 with the cp949 locale before the encoding fix and found
implicit file-encoding failures. That report is not a passing native Windows run
of the corrected code.

After making file encodings explicit, all 18 tests passed on Linux with Python
3.14.4, both normally and with the emulated cp949 file default. The new CLI test
failed at `author.py doctor` before the runtime fix and passed afterward. The
differential audit also covered 9,454 inputs under the emulated default with no
unexpected verdict/path differences. A native cp949 Windows rerun of the corrected
code remains outstanding; the emulation does not replace it.

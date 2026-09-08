# Atlas assembly and lazy detail pages

Run paths relative to the actual installed skills. `atlas.py` uses code-flow's maintained IR, bundled validator and canvas renderer. Python 3.10+ is sufficient; no additional Python packages or repository development scripts are required.

## Choose the output and retain the inputs

Choose the HTML path before authoring. Without a user path or repository policy, use `$SOURCE_ROOT/docs/atlas/<project-key>.html`. The default internal directory is `<HTML directory>/_internal/<HTML filename without extension>/`; language suffixes remain part of that name. For example, `project.en.html` uses `_internal/project.en/`. A repository policy or user-selected private directory takes precedence: pass it as `--internal-dir` on every build.

~~~sh
ATLAS_HTML="$SOURCE_ROOT/docs/atlas/project-key.html"
ATLAS_INTERNAL="$SOURCE_ROOT/docs/atlas/_internal/project-key"
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" doctor
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" init \
  --source-root "$SOURCE_ROOT" --module package --target package \
  --question '이 프로젝트의 목적과 주요 구성을 설명해 줘' --title '프로젝트 구성' \
  --include '패키지 공개 기능과 내부 책임' --exclude '외부 서비스 내부' \
  --profile library-sdk --output "$ATLAS_INTERNAL/atlas.internal.json"
~~~

The draft is insufficient until source reading supplies actual facts. If it already exists, read and update it rather than running `init` again; `init` refuses overwrites. `code-flow/scripts/author.py capture` works on this internal IR. Evidence anchors stay internal. Use the companion's assembly protocol for claim statuses, source snapshots and rendering restrictions.

Use `layer: atlas` and `subject.kind: project`. `nodes` are responsibilities/components, `edges` are observed relationships, and `regions` are evidence-backed, non-overlapping groups of node IDs. A one-node map can omit regions and edges. The common core/detail field hides optional detail until requested; entering a region shows all its nodes and their immediate, explicitly connected neighbors.

Every `subjects` entry is a scoped capability with these fields:

- `id`, `kind`, `question`, `module`, `targets`, `scope`: copy the actual resolved behavior subject identity and included/excluded scope. New targets should record their file/symbol. When an existing behavior subject has label-only targets, preserve that identity and resolve its entry locations through explicit code/config evidence. The generation request carries both targets and evidence locations. `kind` is capability, workflow or lifecycle.
- `label`, `summary`, `nodeId`: the short description and responsible map component.
- `confidence`, `supportStatus`, `verificationNote`, `evidenceIds`: independently review the capability's presence/ownership. Evidence IDs refer to the map's evidence set.
- `link`: relative future behavior HTML URL and `generated: false` with a draft `command`. The builder replaces the command with the precise subject/target/scope request and determines availability from current files. Never mark a file generated based only on its existence.

Older minimal catalog entries remain readable by the shared renderer; new atlas authoring requires scoped entries. The schema remains the unfrozen 0.1.0 draft, and the common authoring bundle is 0.8.0.

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" build \
  "$ATLAS_INTERNAL/atlas.internal.json" --source-root "$SOURCE_ROOT" \
  --output "$ATLAS_HTML" --data-output "$ATLAS_INTERNAL/atlas.render.json"
~~~

This creates the map only and retains `atlas.internal.json` and an initially empty `pages.json`. The optional `atlas.render.json` has already lost verification anchors and may have pruned claims; it is not a substitute for the internal input. The HTML does not fetch any of these files at runtime.

## Add only requested details

Missing pages have copyable host requests; the browser never runs generation. After the user requests a capability, use code-flow to trace it, and optionally visual-primer for its rules. Keep the reviewed graphs and original authored layout in the map's internal directory. Supply only the requested inputs in a separate `requested-pages.json`, for example:

~~~json
[
  {
    "behavior": "detail-agent.behavior.internal.json",
    "output": "agent-run.html",
    "logic": "detail-agent.logic.internal.json",
    "layout": "detail-agent.layout.json",
    "logicOutput": "agent-rules.html"
  }
]
~~~

Input paths are relative to the manifest. Output paths are relative to the atlas HTML's directory. Omit all three logic fields when only behavior is requested. The behavior output must match its catalog URL; different folders and URL-encoded filenames are supported. For the final business-logic drill-down, `layout` should use visual-primer's authored version 2: topic-specific HTML/SVG and optional interactions bound to reviewed rules/claims. The same manifest/build connects this picture lesson to the map and behavior. Existing version 1 compact rule layouts remain compatible.

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" build \
  "$ATLAS_INTERNAL/atlas.internal.json" --source-root "$SOURCE_ROOT" \
  --pages "$ATLAS_INTERNAL/requested-pages.json" --output "$ATLAS_HTML"
~~~

The builder prepares and validates every requested page before writing them, adds atlas links to the details, and adds matching behavior/rules links. It retains the unpruned, linked inputs as `atlas.internal.json`, `detail-<subject-id>.behavior.internal.json`, and, when supplied, `detail-<subject-id>.logic.internal.json` and `detail-<subject-id>.layout.json`. Subject IDs are filename-escaped; the `detail-` prefix avoids Windows device names. It merges their relative input/output paths into `pages.json`, preserving previously saved entries and unrequested child files. A behavior-only refresh also preserves its saved rules/layout for future review. Use `requested-pages.json` for a subset; do not replace the retained `pages.json` with that subset.

HTML and retained JSON are staged only after all rendering and storage checks succeed. Files are replaced individually; this is not a transactional directory swap, and a write failure may require rerunning the build. Existing HTML and internal graph identity prevent replacing another repository, subject, scope, layer or language. Keep HTML/render JSON separate from authoring inputs. Rebuilding from the retained input paths is supported; the builder updates those inputs with links, never with pruned render data.

The map checks catalog target/scope/language, the source snapshot and an active return link to this map. A missing, incompatible, stale or one-way detail remains a generation request. To add the return link to an existing detail, explicitly supply its internal input in the pages manifest. Pages that were not requested are neither generated nor rewritten. Rebuild the map after generating another child to refresh its availability.

Map-to-detail navigation carries the current region, selection, camera and layout dimensions as URL state; returning uses the atlas URL recorded in the detail, never a supplied external destination. Camera coordinates are restored only for matching dimensions; after resizing or when opening an older link, the selected item is framed in the current layout. Browser storage is not required. These local links require the HTML files to be available and do not publish them.

## Re-render, refresh and share

For an explicitly requested re-render of the map and all retained details, use the saved inputs directly:

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" build \
  "$ATLAS_INTERNAL/atlas.internal.json" --source-root "$SOURCE_ROOT" \
  --pages "$ATLAS_INTERNAL/pages.json" --output "$ATLAS_HTML"
~~~

Omit `--pages` for a map-only refresh; saved children are not implicitly loaded, generated or rewritten. The retained list is a regeneration inventory, not a claim that every page remains current. Inspect it before replaying if catalog targets or output paths have changed; deliberately update the affected entries without deleting unrelated inputs.

For presentation-only changes, reuse the graphs and edit only the needed layout/template. The normal source snapshot/evidence checks still run. A changed commit requires source review; same-commit source drift can invalidate claims and withhold dependent pictures. Reread affected implementation and dependent claims before updating their evidence and explanations. Do not refresh hashes just to pass checks. This storage feature does not implement automatic Git-diff analysis or partial HTML patching: explicitly requested pages are rendered as complete files.

For old outputs, locate their original internal graphs/layouts and supply them once to `build`; they are copied into the new bundle without deleting the originals. HTML or render JSON alone cannot recover lost verification anchors or the full authored layout.

Retain the bundle for future authoring, but exclude the **entire `_internal/` directory** (or custom private directory) from HTML sharing, archive exports and static-site publishing. It may contain source excerpts and executable presentation code. An underscore is a naming convention, not access control. Share only the reviewed, linked HTML files with their relative structure intact.

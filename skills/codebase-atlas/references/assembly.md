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

Use `layer: atlas` and `subject.kind: project`. `nodes` are responsibilities/components, `edges` are observed relationships, and `regions` are evidence-backed areas. Sibling regions have disjoint membership; a parent includes its children's node IDs. A one-node map can omit regions and edges. The detailed structure view can still show a region's members and their immediate recorded neighbors.

Optional region fields support the area overview without breaking existing inputs:

- `interface: {inputs: string[], activity: string, outputs: string[]}`: short, reviewed descriptions of what comes in, what the area does, and what it produces. The region's evidence must support all these claims. Empty arrays mean no recorded items; an omitted interface shows an explicit unrecorded state.
- Optional interface `actor` names who performs the work; `entryLabel` says what the area action opens. Use everyday terms and a short verb phrase for `activity`.
- Optional interface `example` has `kind: illustrative` and `input`/`output` artifacts. Each artifact has `type: request|record|page|selection`, `title`, and a nonempty string array `items`. These are short explanatory examples rendered as literal text, not source bodies, arbitrary HTML or executed results. The renderer labels them as examples and withholds their artifacts when the region is not confirmed. Keep canonical inputs/outputs visible beside the example. Omit examples when they add no understanding.
- `parentId`: another region's ID. Parents must exist, be acyclic and contain every child member. Overlap is valid only along this ancestry; shared dependencies use edges. Unsupported parents withhold descendant regions instead of promoting them to invented root areas.
- `role: primary|support`: optionally separates cross-cutting support from the main areas. Legacy groups whose members are all detail nodes appear in support by default.

The renderer groups boundary edges by peer area, direction, relation type and test context. It retains the original edge IDs and labels. It never creates transfers from interface text or group order. No extra handoff graph needs to be authored.

Every `subjects` entry is a scoped capability with these fields:

- `id`, `kind`, `question`, `module`, `targets`, `scope`: copy the actual resolved behavior subject identity and included/excluded scope. New targets should record their file/symbol. When an existing behavior subject has label-only targets, preserve that identity and resolve its entry locations through explicit code/config evidence. The generation request carries both targets and evidence locations. `kind` is capability, workflow or lifecycle.
- `label`, `summary`, `nodeId`: the short description and responsible map component.
- `confidence`, `supportStatus`, `verificationNote`, `evidenceIds`: independently review the capability's presence/ownership. Evidence IDs refer to the map's evidence set.
- `link`: relative future behavior HTML URL and `generated: false` with a draft `command`. The builder replaces the command with the precise subject/target/scope request and determines availability from current files. Never mark a file generated based only on its existence.

Older minimal catalog entries remain readable by the shared renderer; new atlas authoring requires scoped entries. The schema remains the unfrozen 0.1.0 draft, and the common authoring bundle is 0.8.0.

## Composition and feature workspace

For the current project overview, add `composition: {regionIds, edgeIds}`. These
IDs select reviewed architectural groups and relationships from the atlas. The
selected regions' node membership defines the visible components; every selected
edge must have both endpoints among them. Use real service/package/environment/
storage boundaries. Removed unsupported groups also remove their composition
references and unavailable connections.

The builder adds `featureDetails` to the public render graph only. Each entry is a
checked public behavior graph for one available catalog subject, retaining its
identity, summary input/output, nodes, edges, scenarios and evidence status. It
uses the prepared requested child or an already linked child after the normal
identity and current-source checks. It never embeds internal anchors, accepts an
unrelated scope, merges shared owners, or rewrites an unrequested child. This
projection is not saved into the private authoring atlas.

The first screen shows project composition, then a concise group per capability.
Place incoming request/data → produced result above responsibility boxes. Author
these as the child's evidence-backed `regions` with `role: primary`, a short label,
one-sentence summary and disjoint `nodeIds`. The member nodes are the detailed
processing steps, not separate top-level boxes. Only crossing edges appear in the
summary; internal checks, branches and scenario selection remain in the detail.
Box links open their processing list through the region's `item` ID. A process
node leads to its rule pictures. Without reviewed primary groups, show the I/O and
detail action rather than repeating the detailed graph. A missing/stale child
keeps an explicit gap and request. Return state focuses the feature heading.
The old `area` field and region interfaces remain available for retained atlases
without `composition`.

Keep the full component diagram, searchable catalog, package tree and evidence
inspection available. Follow [maintenance-story.md](maintenance-story.md) for the
information a first-time maintainer needs.

Selecting a capability from the catalog opens a wide summary dialog (full-screen on small phones), with no permanent side pane. It shows the capability's own status, owner, a representative path, direct relationships and rule summaries. Other paths, source evidence, related flows, rule conditions/reasons/exceptions, tests and scope open on demand; these are not removed from the data. The fixed actions reach the existing precise detail page or diagram. Connections are not an exhaustive change-impact analysis. No feature or dialog opens automatically. Dismissal preserves selection, filters and page scroll, returning focus to the invoking card. Choosing a capability from search or a tree item's capability action opens its dialog; restored detail links highlight/focus the card without reopening it. Dialog state is local, not a new URL field. Close the dialog before opening search, a tree path or the diagram; clipboard fallback must remain usable inside it.

Scenarios are related when a step references the owner node or an edge touching that owner. Render each matching scenario intact; never splice matching steps into a new sequence. **A shared owner does not establish an exact capability trace.** Label these as component-related flows and use the existing scoped detail page for precise behavior. Numbers mean explanation order, not runtime tracing. Preserve conditions, non-normal branches and `execution: parallel|unordered`. No matching scenarios means no contextual flow section; the full diagram still offers all recorded scenarios. Do not turn a capability list or folder order into an execution scenario.

Cautions select existing `rules` through owner `nodeIds`, retaining each rule's own status, conditions/outcomes and expandable rationale/exceptions/evidence. Shared-component rules are not automatically exclusive to the selected capability. A caution summary does not replace the deeper picture-first lesson. Rules with `numeric: true` **or numeric text** are removed before rendering unless evidence and claim are confirmed; do not evade the safeguard by rewording an unsupported number.

Project conventions in `CLAUDE.md`, `CONTRIBUTING.md` or similar documents may support evidence `kind: documentation`. This establishes **what the document says**, not **that all code follows it**. Phrase these as stated conventions and verify implementation separately before claiming compliance. The entry displays that distinction. Test evidence appears only when `kind: test` locations are explicitly attached to the capability or its owner. Recorded test locations are not passing test results. Missing mappings mean “not recorded,” not “no tests.”

Keep decision-critical unresolved items and high-severity warnings concise. The entry surfaces the first high-severity warning, unresolved item or limitation before the cards, with a visible control to expand all analysis gaps. Record full unresolved questions in `analysis.unresolved`, limitations in `summary.limitations`, exclusions in `subject.scope.excludes`, and follow-up checks in `analysis.nextAttempts`. The compact top review label counts confirmed non-context nodes, regions, capabilities and structure entries among **recorded render items**; legacy capabilities inherit their owner's status. It is neither whole-repository completeness nor test coverage. Pruned items are outside its denominator, so record missing scope explicitly.

The optional atlas-only `structureEntries` array records reviewed physical landmarks:

- `id`: globally unique claim ID.
- `path`: canonical, literal source-root-relative path using forward slashes; `.` means the project root. No absolute paths, traversal, URL encoding, redundant slashes or trailing slash.
- `kind`: `package`, `directory`, or `file`. A package needs source-reviewed manifest/build semantics, not just a directory name.
- `label`, `summary`: short plain-language role/name and explanation; the real path is displayed separately.
- `nodeIds`: reviewed owner components (may be empty). These enable diagram/capability navigation; they create no edges.
- `confidence`, `supportStatus`, `verificationNote`, `evidenceIds` and optional `sourceIds`: the same reviewed-claim contract as regions. At least one code/config evidence location must be at the file path, or inside the directory/package. Root entries may cite any local code/config file.

For example, after reviewing a real `src/orders` directory and its local evidence:

~~~json
{
  "id": "structure-orders",
  "path": "src/orders",
  "kind": "directory",
  "label": "Order handling",
  "summary": "Accepts order requests and chooses their processing path.",
  "nodeIds": ["node-orders"],
  "confidence": "resolved",
  "supportStatus": "supported",
  "verificationNote": "Checked request handlers and their implementation.",
  "evidenceIds": ["ev-order-handler"]
}
~~~

This is a field example, not a discovered project fact: replace all paths, IDs and claims with actual reviewed input. Paths must be unique. The viewer nests an entry below its closest recorded ancestor; it does not invent roles for omitted intermediate directories. A file cannot be a parent. Unsupported structure claims are omitted, failed source rereads get unverified badges, and references to omitted owners are removed. Structures are retained in `atlas.internal.json` through normal builds. Older JSON without this array remains valid and shows an explicit unrecorded-structure message, not an invented folder map.

Feature existence/ownership, evidence confidence, and detail availability are independent. Catalog filters cover labels, summaries, symbols, modules and target/associated structure paths, responsibility region and detail availability. The visible Find button or Ctrl/Cmd+K searches capabilities, non-context components and structure paths. Capability results clear filters and open the summary dialog with the chosen card as its return destination; component results open the diagram; path results open the tree and recorded ancestors. The catalog counts only recorded capabilities, never all project functionality. Missing-detail buttons copy a precise host request; the offline page does not run AI.

## Build the map

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

Map-to-detail navigation carries either the overview's search, filters and selected capability, or the diagram's current region, selection, camera and layout dimensions as URL state. New overview links omit `tab`; old `tab=roles|files` values are still validated and accepted but have no display effect. Folder expansion is local UI state, not retained across pages. Returning uses the atlas URL recorded in the detail, never a supplied external destination. A direct diagram selection returns to the matching component; catalog-only entries remain reachable in the expanded catalog. Node lesson links pass `s2s-node` and `s2s-behavior`; the lesson uses rule-to-node bindings and restores the selected behavior location through its own checked behavior link. Camera coordinates are restored only for matching dimensions; after resizing or when opening an older link, the selected item is framed in the current layout. Browser storage is not required. These local links require the HTML files to be available and do not publish them.

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

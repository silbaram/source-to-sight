# Atlas assembly and lazy detail pages

Run paths relative to the actual installed skills. `atlas.py` uses code-flow's maintained IR and canvas renderer; it does not require repository development scripts. Install its shared Python requirements from the companion when absent.

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" doctor
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" init \
  --source-root "$SOURCE_ROOT" --module package --target package \
  --question '이 프로젝트의 목적과 주요 구성을 설명해 줘' --title '프로젝트 구성' \
  --include '패키지 공개 기능과 내부 책임' --exclude '외부 서비스 내부' \
  --profile library-sdk --output build/atlas.internal.json
~~~

The draft is insufficient until source reading supplies actual facts. `code-flow/scripts/author.py capture` works on this internal IR. Evidence anchors stay internal. Use the companion's assembly protocol for claim statuses, source snapshots and rendering restrictions.

Use `layer: atlas` and `subject.kind: project`. `nodes` are responsibilities/components, `edges` are observed relationships, and `regions` are evidence-backed, non-overlapping groups of node IDs. A one-node map can omit regions and edges. The common core/detail field hides optional detail until requested; entering a region shows all its nodes and their immediate, explicitly connected neighbors.

Every `subjects` entry is a scoped capability with these fields:

- `id`, `kind`, `question`, `module`, `targets`, `scope`: copy the actual resolved behavior subject identity and included/excluded scope. New targets should record their file/symbol. When an existing behavior subject has label-only targets, preserve that identity and resolve its entry locations through explicit code/config evidence. The generation request carries both targets and evidence locations. `kind` is capability, workflow or lifecycle.
- `label`, `summary`, `nodeId`: the short description and responsible map component.
- `confidence`, `supportStatus`, `verificationNote`, `evidenceIds`: independently review the capability's presence/ownership. Evidence IDs refer to the map's evidence set.
- `link`: relative future behavior HTML URL and `generated: false` with a draft `command`. The builder replaces the command with the precise subject/target/scope request and determines availability from current files. Never mark a file generated based only on its existence.

Older minimal catalog entries remain readable by the shared renderer; new atlas authoring requires scoped entries. The schema remains the unfrozen 0.1.0 draft, and the common authoring bundle is 0.6.0.

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" build \
  build/atlas.internal.json --source-root "$SOURCE_ROOT" \
  --output build/project.html --data-output build/project.render.json
~~~

This creates the map only. Missing pages have copyable host requests; the browser never runs generation. After the user requests a capability, use code-flow to trace it, and optionally visual-primer for its rules. Supply only those reviewed inputs in a pages manifest:

~~~json
[
  {
    "behavior": "agent.internal.json",
    "output": "agent-run.html",
    "logic": "agent-rules.internal.json",
    "layout": "agent-rules.layout.json",
    "logicOutput": "agent-rules.html"
  }
]
~~~

Input paths are relative to the manifest. Output paths are relative to the atlas HTML's directory. Omit all three logic fields when only behavior is requested. The behavior output must match its catalog URL; different folders and URL-encoded filenames are supported.

~~~sh
python3 "$ATLAS_ROOT/scripts/atlas.py" --code-flow-root "$FLOW_ROOT" build \
  build/atlas.internal.json --source-root "$SOURCE_ROOT" --pages build/pages.json \
  --output build/project.html --data-output build/project.render.json
~~~

The builder prepares and validates every requested page before writing them, adds atlas links to the details, and adds matching behavior/rules links. Files are replaced individually after all rendering succeeds; this is not a transactional directory swap. Existing destination metadata prevents replacing another repository, subject, scope, layer or language. Keep inputs separate from output paths.

The map checks catalog target/scope/language, the source snapshot and an active return link to this map. A missing, incompatible, stale or one-way detail remains a generation request. To add the return link to an existing detail, explicitly supply its internal input in the pages manifest. Pages that were not requested are neither generated nor rewritten. Rebuild the map after generating another child to refresh its availability.

Map-to-detail navigation carries the current region, selection, camera and layout dimensions as URL state; returning uses the atlas URL recorded in the detail, never a supplied external destination. Camera coordinates are restored only for matching dimensions; after resizing or when opening an older link, the selected item is framed in the current layout. Browser storage is not required. These local links require the HTML files to be available and do not publish them.

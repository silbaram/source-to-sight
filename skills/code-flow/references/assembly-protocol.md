# Assemble a source-grounded page

The installed `code-flow` folder contains all rendering resources. Set the examples' `SKILL_ROOT` and `SOURCE_ROOT` to the actual paths; they are ordinary shell variables, not host-specific configuration.

```sh
python3 -m pip install -r "$SKILL_ROOT/scripts/requirements.txt"
python3 "$SKILL_ROOT/scripts/author.py" doctor
```

Python 3.10+ and the declared `jsonschema` dependency are required. Rendering needs no Node, CDN, sibling skill, or target-project dependency. Install dependencies in an appropriate existing environment; the rendering commands make no network requests.

## Draft and evidence

Create a local working IR outside the intended shareable output. Supply the resolved module/target and actual scope, rather than using the user's question as a universal target ID.

```sh
python3 "$SKILL_ROOT/scripts/author.py" init \
  --source-root "$SOURCE_ROOT" --question 'Explain the selected capability' \
  --title 'Capability title' --module 'package-name' --target 'publicSymbol' \
  --include 'The selected path and its completion boundary' \
  --exclude 'Explicitly excluded alternate behavior' \
  --profile library-sdk --language en --output work/graph.json
```

`init` refuses to overwrite an existing draft. It creates a valid **insufficient** graph with no invented nodes and a stable scope-derived subject key. It records the actual Git snapshot when available; archives without Git stay unknown. `--model` records the actual model identifier if known; otherwise leave it null. `--repository` can supply a logical source ID for an archive.

After reading a relevant range, capture it. Choose an exact nonblank anchor line within that range; the default is the first nonblank line. This command records evidence only, not a node or a supported semantic claim.

```sh
python3 "$SKILL_ROOT/scripts/author.py" capture work/graph.json \
  --source-root "$SOURCE_ROOT" --id ev-public-entry \
  --file src/component.py --symbol publicSymbol --start 20 --end 44
```

Paths and lines above illustrate the command; substitute actual locations. Duplicate IDs are rejected. Do not refresh an old evidence hash independently of the dependent claims: reread them and deliberately edit the internal graph.

## Author the IR

Use the [internal schema](ir-internal-v0.1.0.schema.json) and [renderer contract](renderer-contract.md). `init` supplies every required root field; populate only factual graph content:

| Field | Authoring rule |
| --- | --- |
| `subject.targets`, `scope` | Actual symbols/configuration and includes/excludes; keep regeneration identity aligned |
| `analysis` | Actual searched files/areas, unresolved alternatives, next attempts; complete only for the stated scope |
| `summary` | Purpose, inputs/results, decision-relevant limitations in the output language |
| `nodes`, `actions` | Role, readable label/summary, optional identifier, importance, evidence and claim-specific review |
| `edges` | Existing endpoints, semantic type/derivation, evidence of the relationship itself |
| `scenarios` | Optional; every step has exactly one node or edge reference and independently checked caption. Use `kind`, step `branch`, and optional `condition`/`execution` for the path semantics in [complex behavior](complex-behavior.md) |
| `stateTransitions` | Owner, before/after, exact trigger condition, explanation and evidence |
| `rules` | Reviewed conditions/results, optional `rationale` and `exceptions`; numerical content in any of these fields needs confirmed evidence |
| `warnings` | Structured uncertainty/candidates with valid references; not hidden disclaimers |
| `links` | Relative URLs for matching subjects/scopes/languages; precise generation request if missing |

For a factual node include `contextOnly:false`, `actions:[]`, `importance:core|detail`, and the shared claim fields (`confidence`, `supportStatus`, `verificationNote`, `evidenceIds`). A context-only actor omits those claim fields. The schema lists the finite node/edge/derivation vocabulary; do not invent a profile-specific variant.

`confidence` and `supportStatus` remain the author's semantic decisions. Reread the evidence against every claim, including captions. File hash equality does not justify changing uncertain to supported. Set `provenance.description` to what was actually performed and keep `humanReviewed:false` until a human has reviewed this result. Update or remove draft placeholders before presenting a finished explanation.

## Build and inspect

```sh
python3 "$SKILL_ROOT/scripts/s2s.py" validate work/graph.json
python3 "$SKILL_ROOT/scripts/author.py" build work/graph.json \
  --source-root "$SOURCE_ROOT" --output "$SOURCE_ROOT/docs/flows/subject-key.html" \
  --data-output work/render.json
python3 "$SKILL_ROOT/scripts/s2s.py" inspect "$SOURCE_ROOT/docs/flows/subject-key.html"
```

Use the generated subject key or the user's explicit destination. For multiple languages, use separate suffixed paths. `build` checks the current source commit, rereads every evidence range/hash, refreshes working-tree cleanliness, validates/prunes unsupported claims, and removes anchors before rendering. It rejects output collisions with another repository/subject/scope/language and keeps internal/render/HTML files separate. Source edits within the same commit become unverified through the existing evidence check; a different or unverifiable commit requires renewed discovery.

The scripts cannot certify arbitrary prose or independently enforce all target-code secrecy. Inspect the full output, including embedded JSON, for source excerpts and original target prompts. The user's explanation question can remain as regeneration metadata; target-project prompt templates cannot.

Open the HTML, select nodes/edges and any state/region entries, step through scenarios if present, and check a narrow viewport. Confirm labels fit, connections touch the correct nodes, scope/uncertainty are visible, and generated links reach the same subject. A partially verified page is a valid deliverable when honestly labeled.

Create related pages before refreshing their parent links. For `--explain`, follow the [rule checklist](rule-checklist.md), use `author.py explain` to draft from the internal behavior graph, and locate the actual installed `visual-primer` source-rules instructions. The pair builder preserves the behavior's facts, rereads evidence, validates both destinations, and renders both pages before replacing either file. Its newly prepared pages resolve each other's links without relying on old HTML. Missing sibling skills do not prevent the behavior page. Generated HTML can only navigate or copy a generation request; it cannot launch a model or create a new page offline.

When the request comes from a project map, preserve the catalog's subject ID, kind, module, targets and included/excluded scope. Locate the installed `codebase-atlas` assembly instructions and pass only the requested internal behavior graph (and optional reviewed logic/layout) to its pages manifest. That builder validates the map and both detail layers together, supplies return links and refreshes availability. Do not silently substitute another scope or generate the whole catalog.

# M0 fixture provenance

These fixtures validate the common contract and renderer. They are not the M1.5 golden set. Source relationships were read and recorded by the coding agent; independent human fact review is pending.

| Fixture | Type | Provenance |
| --- | --- | --- |
| `utility-minimum` | CLI/utility, one public function | Actual JavaScript source: strip-ansi |
| `framework-plugin` | Plugin lifecycle and dispatch | Actual Python source: pluggy |
| `agent-run` | Agent loop, model boundary, tool dispatch | Actual Python source: smolagents |
| `web-request` | Web request | Synthetic |
| `cli-transform` | File transformation, detailed action, conditional state transition | Synthetic; the state trigger is separate from its summary |
| `library-use` | Resource usage lifecycle | Synthetic |
| `data-pipeline` | Fan-out/fan-in, no total order | Synthetic |
| `adversarial` | Eleven nodes, branch, loopback, orphan, two candidates, invalid location | Synthetic; invalid location is intentional |
| `insufficient` | Missing evidence | Synthetic; no graph is appropriate |
| `utility-atlas` | Small project-map contract | Same strip-ansi evidence; tests regions and subject links |
| `utility-logic` | Rules contract | Same strip-ansi evidence; tests paired subject identity |

## Pinned source readings

- **strip-ansi:** [index.js, lines 5–19](https://github.com/chalk/strip-ansi/blob/38ff9f2282540422031ed523f0060c7bb575e20f/index.js#L5). Checks string input, skips matching when no introducer exists, and removes matches. No wrapper application, server, or database is invented.
- **pluggy:** [registration and dispatch](https://github.com/pytest-dev/pluggy/blob/4821148db2f4c6daa62ad8bdcae2918ecf27a731/src/pluggy/_manager.py#L97), [public hook call](https://github.com/pytest-dev/pluggy/blob/4821148db2f4c6daa62ad8bdcae2918ecf27a731/src/pluggy/_hooks.py#L527), [implementation invocation](https://github.com/pytest-dev/pluggy/blob/4821148db2f4c6daa62ad8bdcae2918ecf27a731/src/pluggy/_callers.py#L82). Registration does not automatically execute the hook; the scenario explicitly identifies the later caller request. Concrete installed plugins are unresolved.
- **smolagents:** [run and loop](https://github.com/huggingface/smolagents/blob/30bb1161095dbae2271e6bc3cc4c219cc3897a57/src/smolagents/agents.py#L436), [ToolCallingAgent step](https://github.com/huggingface/smolagents/blob/30bb1161095dbae2271e6bc3cc4c219cc3897a57/src/smolagents/agents.py#L1276), [tool processing](https://github.com/huggingface/smolagents/blob/30bb1161095dbae2271e6bc3cc4c219cc3897a57/src/smolagents/agents.py#L1361). Covers the nonstreaming model path and conditional tool execution; model answers and concrete runtime tool selection remain unresolved.

The immutable repository revisions and files are in [source-repositories.json](source-repositories.json). Fixture evidence includes the source SHA-256. `scripts/fetch_fixture_sources.py` fetches those files into an ignored cache and verifies their recorded hashes. It does not install or run the third-party projects.

Synthetic evidence lives in [sources/synthetic.txt](sources/synthetic.txt), a declarative test model. Its checked locations demonstrate validator behavior; they are not proof of production code behavior.

`scripts/build_fixtures.py` reproduces the author-recorded fixtures. It is a development fixture builder, not an analysis implementation. Changes to real evidence ranges or factual claims require rereading the pinned source and updating this record.

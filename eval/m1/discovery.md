# M1 discovery record

Read on 2026-09-06 by the coding agent, using the installed-skill workflow being developed in this checkout. Sources are pinned in [sources.json](sources.json); evaluation requests are in [cases.json](cases.json). No target project was installed or executed. Search/read operations below describe work actually performed, not an automatic inventory or runtime trace. Evidence ranges and hashes are retained in each graph.

## utility-strip

- Read `package.json`, `readme.md`, the entire `index.js`, and `test.js` to resolve the export and input/output behavior.
- Selected `stripAnsi`, exported from `index.js`. The README's related CLI and stream packages are different targets and were excluded.
- Rechecked the nonstring guard, ESC/CSI fast path, and replacement against the imported matcher. A single factual node answers the chosen scope; no command parser or filesystem is invented.
- The dependency matcher expression is outside this checkout. The page does not promise coverage of every possible terminal control sequence.
- Reused the M0 graph shape after rereading the source; verified its input rule against the implementation, not merely the tests.

## plugin-hooks

- Read the package declaration and README lifecycle example. Searched `register`, `_hookexec`, `_add_hookimpl`, `__call__`, `_multicall`, and hook validation locations.
- Read `PluginManager.register` and `_hookexec`, `HookCaller.__call__`/`_add_hookimpl`, and `_multicall`'s invocation/result branches. Inspected registration-test search results to distinguish the public API from internal operations.
- Selected a normal registration followed by a later host-initiated ordinary hook call. Historic hooks, wrappers, and tracing replacement were excluded rather than silently applying their different behavior.
- Registration adds implementations; it is not itself the ordinary callback invocation. The manager delegates through its default execution function, and the implementation call is in `_multicall`.
- The stored implementation list and first-result option influence execution. Concrete application plugins are unresolved; the page stays partial. Reused M0 geometry/data structure but replaced generic review notes with claim-specific readings.

## agent-tool-loop

- Read package metadata and the README's distinction between agent kinds. Searched `ToolCallingAgent`, `CodeAgent`, run methods, memory append locations, and the agent tests' tool/model cases.
- Read `MultiStepAgent.run`, `_run_stream`, `_handle_max_steps_reached`, `ToolCallingAgent._step_stream`, `process_tool_calls`, and the selection/validation/call portion of `execute_tool_call`.
- Selected nonstreaming return and nonstreaming model generation. Excluded planning, CodeAgent, and callback/final-answer-check internals. The shared method name `run` alone does not resolve the concrete agent behavior.
- The source establishes model/tool boundaries, request recording, per-step recording, final-answer checks, repeated steps, and maximum-step fallback. Multiple tool calls use an execution pool; tool outputs are not universally serial.
- Generation errors propagate; other handled agent errors may be recorded before another iteration. Model responses and concrete tool/managed-agent selection remain unknown. The reused M0 graph now carries explicit per-claim reread notes and these scope limitations.

## library-eviction

- Read `go.mod`, `lru.go` constructor/wrapper methods, `simplelru/lru.go` construction/add/remove paths, and `lru_test.go`'s `TestLRUAdd` case.
- Selected the synchronized public `Cache.Add`; rejected `simplelru.LRU.Add` as the whole public answer and excluded expirable/ARC implementations with similar names.
- Traced constructor registration of the internal buffering callback, the inner new-key insertion and capacity comparison, removal from the list/map, buffer append, and the public wrapper's callback after unlocking.
- Existing-key updates return without eviction; the scenario is explicitly the new-key over-capacity path with a callback registered.
- The state trigger requires the relevant registration and eviction conditions. Actual user callback behavior is unknown, so the public dispatch condition is confirmed while its boundary is uncertain. This case composes library and framework/plugin profiles without a new renderer.

## web-dispatch

- Read `go.mod`, `Router.Handle`, the matching branch of `Router.ServeHTTP`, `node.addRoute`'s registration entry, `node.getValue`'s matching/parameter-return paths, and `TestRouter`.
- Resolved registration and later request dispatch as two entrypoints in one scope. Selected the matching method/path branch, including parameter forwarding; excluded redirect/fallback/method-not-allowed behavior.
- `Handle` writes into the method-specific tree. `ServeHTTP` selects the method tree and invokes the returned function itself; the lookup node does not invent a direct call into the application handler.
- The package establishes handler selection and invocation, not application response contents or a database/service layer. The example remains partial at that external implementation.

## event-receivers

- Read package metadata, README usage, public exports, `Signal.connect`, `Signal.send`, `Signal.receivers_for`, and weak/strong-reference and muted-signal test excerpts.
- Selected synchronous Signal delivery. Rejected the `send_async` and coroutine-adapter paths as different scopes; excluded the auxiliary `receiver_connected` signal from this explanation.
- Registration writes receiver and sender indexes; selection combines matching sender and ANY registrations, removes/skips dead weak references, and yields receiver objects.
- `send` invokes the selected synchronous callable and appends `(receiver, result)` pairs. Muted signals return before that loop. Receiver exceptions propagate. The default receiver order is unspecified, so the graph has no linear recipient playback.
- Concrete subscribers and their output are application-defined. This combines data/event, library, and plugin responsibilities. No durable queue, retry guarantee, transaction, or remote broker is invented.

## Remaining evidence quality checks

The author performed these readings and authored the reference results, so they are not an independent forward test of skill quality. Automated checks verify locations, output constraints, installation, geometry, and interactions. The separate human evidence/comprehension worksheet remains unanswered; no reviewer identity or universal-support result is inferred from these checks.

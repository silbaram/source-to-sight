# Framework and plugin discovery

Look for extension specifications, plugin discovery/loading, registration storage, validation, dispatch, wrappers, and lifecycle teardown. Follow **who invokes whom**, including control returning from the framework into user implementations.

Registration and execution are separate facts. A registration call may validate and store implementations without invoking them. Trace the later host request and dispatch rule before showing a callback invocation. Check historic callbacks or other explicit exceptions to that rule.

Resolve naming conventions, explicit annotations/configuration, priorities, wrappers, and first-result/short-circuit rules from code. Never infer total order from file order or imply every registered plugin runs. When selection is dynamic, show the known rule with unresolved concrete implementations.

Example reading: pluggy's `PluginManager.register`, hook specification checks, `HookCaller.__call__`, `_hookexec`, and `_multicall` establish different parts of registration and dispatch. For ordinary nonhistoric, nonwrapper hooks, state those exclusions. Inspect all corresponding ranges before drawing a single lifecycle across them.

For web frameworks, add the web profile only when routing or UI events are part of the selected capability. The core/extension model does not require Controller/Service/Repository layers.

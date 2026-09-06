# Agent and harness discovery

Resolve the requested run loop, orchestration, evaluation, or harness lifecycle separately. Read the public entrypoint, constructor/configuration, state/memory updates, model interface, tool registry/validation, execution/delegation, termination, error paths, and cleanup that affect that scope.

Distinguish code-controlled behavior from model-dependent choices. Source may establish tool validation and dispatch without identifying the concrete selected tool or its result. Do not represent model reasoning, success, token use, timing, or observed steps unless actual runtime evidence was supplied.

Check streaming and nonstreaming branches separately. Planning, retries, step budgets, stop/final-answer checks, and delegated agents can change the path. Do not reuse the normal-path caption for every branch. Record exactly which branch was read.

Example reading: smolagents has multiple agent classes sharing run machinery. Resolve `MultiStepAgent.run` and `_run_stream` through the selected `ToolCallingAgent` implementation. Trace the model call, tool-call processing, memory recording, and termination checks; the configured model/tool implementations remain external boundaries when absent. `CodeAgent` behavior is not interchangeable with `ToolCallingAgent`.

For harness questions, inspect task loading, run/reset, result collection, scoring, and configuration separately rather than assuming the harness is only the agent loop. Combine data/event or framework/plugin profiles when their responsibility is actually present.

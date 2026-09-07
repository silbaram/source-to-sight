# Web discovery

For fallback routing, read branch precedence and immediate returns before combining redirect, OPTIONS, method errors and missing-route explanations. A redirect response is not an internal rerun of the destination handler. Keep custom middleware/error handlers as unresolved boundaries unless their implementation is also read.

Determine whether the request concerns server handling, a browser/UI event, client state, routing, rendering, or another web capability. HTTP routing is one possible public surface, not the default structure for every project.

For server routing, inspect registration, method/path matching, middleware or wrapper composition, handler selection, response/error boundaries, and external calls that affect the chosen request. Verify redirects and fallback behavior before including them. Do not invent storage or layered controllers/services.

For UI behavior, trace event binding, state updates, effects/data access, and rendering. Separate user interaction from a network call: either can be absent. Trace framework lifecycle rules through the checked-out version and local usage rather than assuming a familiar convention.

Example reading: httprouter `Handle`, the route tree's `addRoute`/`getValue`, and `ServeHTTP` establish registration and later dispatch. For a matching-route scope, include method/path selection and direct handler invocation; exclude redirect/not-found branches explicitly. Registered handlers supplied by applications are a runtime boundary.

Add technical framework notes only after an actual case requires them. Combine library/SDK or framework/plugin when the public package or extension contract is part of the question.

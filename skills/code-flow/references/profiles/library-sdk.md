# Library and SDK discovery

Find the exported API and separate it from similarly named internal helpers. Read construction, ownership, resource lifetime, returns/errors, and allowed usage sequence where relevant. An SDK's transport boundary does not make every library a web application.

For callbacks during mutation or resizing, trace buffer ownership and lock release before the external callback. Check which updates remain if a callback raises, and do not infer rollback or unconditional release from the public API's thread-safe description.

For wrappers, follow the delegation and identify what the wrapper adds: locking, adaptation, retries, callbacks, or error conversion. Do not collapse a wrapper's behavior into the underlying function and lose its contract.

Show independent APIs without imposing a sequence. For a lifecycle, verify acquisition, use, and release paths, including early errors. For concurrency, inspect the actual lock and callback boundaries before claiming atomicity or callback ordering.

Example reading: golang-lru exports a synchronized `Cache` wrapping `simplelru.LRU`. For eviction on `Cache.Add`, read the wrapper, inner insertion/removal, and eviction callback buffering. Determine whether user callbacks happen inside or after unlocking. Exclude expirable/ARC variants unless requested; matching `Add` names do not identify the same implementation.

Combine with framework/plugin for caller-supplied hooks and with data/event for producer/consumer APIs. Keep runtime callback implementations at a boundary if they are not in the checkout.

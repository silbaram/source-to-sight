# CLI and utility discovery

Resolve a command through its executable declaration, parser registration, and handler. Read option defaults, environment/configuration merging, precedence, and exit/error behavior only where they affect the user's question. A public utility function may bypass command parsing entirely.

Follow the actual input conversion and output boundary. Distinguish returning a string from writing stdout/a file. Do not add filesystem, transport, or database nodes merely because those are common CLI concerns.

If the capability is a small function, read the whole function and its direct dependency contract, plus its usage tests. A one-node explanation with actions and no scenario may answer the question completely. Optional fast paths and invalid input still matter.

Example reading: in strip-ansi, inspect `package.json` exports, `index.js`, and `test.js`; resolve the input guard, the no-escape fast path, and the imported matcher boundary. The matcher dependency's internal expression is outside the local implementation unless its source is also inspected. Do not promise that every possible terminal sequence is removed from that local call alone.

Combine with library/SDK for public API contracts or data/event when the command schedules a pipeline. Profile names describe what to read, not which renderer to select.

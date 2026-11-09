**Status:** CLOSED

**Reasons:**
1. **Immediate abort on cancel:** `Promise.race([probe, cancelled])` unblocks `gateOrCancel()` immediately when `cancel()` fires, and `admissionInterrupted()` refuses admission as `shell.CANCELLED` without spawning a job.
2. **Clean resource lifecycle:** `cancelWaiters` registration is pruned in a `finally` block, and `submit`'s `finally` guarantees the status item ends (`begin('check')` -> `end`) on aborted admission.
3. **No unhandled rejections:** `probe.catch(() => undefined)` attaches an error handler immediately, preventing unhandled promise rejections if the background probe rejects after cancel resolves first.

**Regression Risks:**
- **Unload without cancel trigger:** If plugin `dispose()` / unload does not invoke `coordinator.cancel()` (or dispatch `cancelWaiters`), an unload during `check` will still wait for the probe to settle.
- **Synchronous throw in `gate()`:** If `deps.gate()` throws synchronously instead of returning a rejected promise, the exception escapes before `Promise.resolve` / race setup (handled by outer `submit` `finally`, but bypasses `gateOrCancel`).

**Goal-fit score:** 100 / 100


> Orchestrator verification of the two regression risks: (1) `MarkItDownFlowPlugin.onunload()` -> `coord.dispose()` -> `cancel()` (coordinator.ts:277-280), so unload during the check phase releases the waiter immediately; (2) `gate` is `currentGate()` returning a Promise (main.ts:256); a synchronous throw would still be cleaned up by the `finally` in `submit`. M8-01 CLOSED. Goal fit 100.

---
name: seven-model-routing
description: Design resilient provider/model selection and free-tier fallback.
---
# Seven Model Routing
1. Separate provider adapters, model capabilities, routing policy, credentials, and UI selection.
2. Route by task needs (reasoning, code, vision, latency, context window) using verified model metadata.
3. Handle rate limits, timeouts, auth errors, overload and malformed responses distinctly.
4. Use bounded retries with exponential backoff and jitter; switch provider only for retryable failures.
5. Never promise unlimited free usage or fabricate availability; expose fallback status and preserve user choice.
6. Keep API keys in managed secret storage or environment configuration, never hard-code them.
7. Test provider failure, exhausted quota, cancellation, streaming, timeout and fallback loops.

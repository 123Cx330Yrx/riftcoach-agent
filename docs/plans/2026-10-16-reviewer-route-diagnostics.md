# Reviewer route diagnostics and recovery

## Decision

The 2026-10-16 live batch is closed after its first request. The request hook
counted one HTTP attempt, but no response headers, body bytes, or usage receipt
were observed. The old direct-only transport could not use the machine's local
HTTP proxy, so the remaining calls must not be redelivered from that batch.

## Evidence

- Direct TCP to the provider endpoint was refused.
- The default local network path reached the endpoint and returned an
  unauthenticated response without a model request.
- The batch receipt retains unknown usage and remains unqualified.

## Implementation

- Pre-header transport failures now retain a fixed category such as
  `connect_error` or `connect_timeout` in the body-free observation.
- The supervisor preserves the worker's stable failure code and records the
  fixed category separately; a missing usage checkpoint no longer hides a
  worker failure.
- Reviewer profiles can explicitly select `direct-no-proxy` or the verified
  local `proxy-12000` route. The default remains direct and environment proxy
  variables are never implicitly consumed.

## Boundary

This change is an offline reliability fix. It does not authorize a new model
request, select a provider for the product, or qualify any report. A fresh
batch needs its own exact HEAD/CI proof, route preflight, and cost authorization.

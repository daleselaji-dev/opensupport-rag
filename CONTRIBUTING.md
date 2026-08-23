# Contributing to OpenSupport

1. Reproduce the current environment with the README and run `pytest`.
2. Keep real source provenance, data policy and authority labels intact.
3. Add or change one assembly component at a time.
4. Run the same frozen Benchmark before and after the change.
5. Report quality, latency, cost and failure slices; do not report only an
   average score.
6. Never commit complaint exports, raw snapshots, model weights, credentials or
   `.env` files.

Pull requests that change retrieval or generation must include the relevant
Trace shape, Eval artifact and known limitations.

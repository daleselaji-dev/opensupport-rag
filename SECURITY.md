# Security policy

OpenSupport is a local-first educational and portfolio project. It must not be
used to make legal, financial, refund, account or regulatory decisions without
qualified human review.

## In scope

- Prompt injection or indirect document injection;
- PII leakage from complaint text, logs, traces or source snapshots;
- Cross-source or cross-role retrieval leakage;
- Citation validation bypasses;
- Unsafe Agent actions or approval bypasses;
- Index poisoning, stale source activation or rollback failures.

Please open a private security report rather than publishing sensitive data in
an issue. Do not include real account numbers, credentials, API keys or private
complaint exports.

## Current controls

- Complaint narratives are labeled consumer allegations;
- Source URLs, hashes and index versions are recorded;
- Citation IDs are checked deterministically;
- Low citation coverage and dangerous claims fail closed to human review;
- Agent actions remain disabled until production RAG gates pass.

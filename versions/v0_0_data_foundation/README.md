# V0.0 Data Foundation

This is the first production concern, before Dense RAG quality comparisons.

```text
real CFPB source
→ download/parse
→ normalize + validate
→ exact identity/content deduplication
→ metadata + language + hashes
→ quality report + quarantine
→ derived Embedding/Qdrant index
```

Trace and artifacts:

- `data/data_quality_latest.json`
- `data/ingest_manifest.json`
- `snapshot_id`
- source URL, content SHA256 and normalized text SHA256
- accepted, duplicate and quarantined counts

Gate: at least 200 unique complaints for the first acceptance run, duplicate
count 0, Manifest/Qdrant consistency, and an explanation for every quarantined
record. PostgreSQL/MinIO persistence is the next adapter behind the same
contract; JSON is the local first-step artifact.

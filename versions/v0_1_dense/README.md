# V0.1 Dense baseline

```text
Question → Qwen Embedding → Qdrant Dense
         → official guidance + complaint evidence
         → compact prompt → DeepSeek-R1 → citation validation
```

Trace: `query_received → embed_query → retrieve_guidance → retrieve_complaints → assemble_context → generate_answer → validate_citations`.

Gate: real CFPB data, deterministic chunk IDs, source authority separation, citations, no refund/legal/account decisions. Current data gate remains incomplete until 200 unique complaints and a consistent Manifest are available.

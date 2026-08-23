# OpenSupport infrastructure profiles

The local learning path still works with Qdrant only. The production profile
adds the services below without replacing the current FastAPI/Qdrant API:

```powershell
docker compose --profile core up -d
docker compose --profile core ps
```

- PostgreSQL on `localhost:15432`: source metadata, document versions, chunks,
  ingestion jobs, index versions, Eval runs and Agent drafts.
- MinIO on `localhost:19000` (console `19001`): raw HTML/JSON/PDF snapshots.
- Redis on `localhost:16379`: Celery broker/backend and cache.
- Qdrant on `localhost:16333`: derived Dense/Sparse retrieval index.

The SQL schema in `postgres/001_data_foundation.sql` is deliberately mounted as
an initialization script. The current V0.0 API writes a deterministic JSON
quality report first; the PostgreSQL/MinIO persistence adapter is the next
implementation step after this contract has passed local tests.

Observability and graph services are separate profiles so a learner can keep
the core stack small:

```powershell
docker compose --profile observability --profile graph up -d
```

The observability profile exposes Prometheus on `19090`, Grafana on `13001` and
OTLP HTTP/GRPC on `14318`/`14317`. The FastAPI `/metrics` endpoint records request
count, error count and duration; the OpenTelemetry Collector receives API spans
without making the query path depend on the collector being online.

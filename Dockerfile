FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-production.txt
# Keep the optional Graph profile reproducible even when an older cached base
# layer was built before the Neo4j dependency was added.
RUN pip install --no-cache-dir "neo4j>=5.28,<6"
COPY requirements-reranker.txt ./
ARG INSTALL_RERANKER=false
RUN if [ "$INSTALL_RERANKER" = "true" ]; then pip install --no-cache-dir -r requirements-reranker.txt; fi
COPY app ./app
COPY static ./static
COPY docs ./docs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

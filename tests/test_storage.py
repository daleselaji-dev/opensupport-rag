import asyncio

from app.config import Settings
from app.storage import SourceOfTruthStore


def test_postgres_dsn_accepts_sqlalchemy_style_url():
    store = SourceOfTruthStore(Settings(postgres_url="postgresql+psycopg://u:p@localhost/db"))
    assert store.postgres_dsn == "postgresql://u:p@localhost/db"


def test_storage_probe_is_explicit_for_local_learning_mode():
    store = SourceOfTruthStore(Settings(storage_probe_enabled=False))
    assert asyncio.run(store.health()) == {
        "postgres": "not_probed",
        "minio": "not_probed",
        "redis": "not_probed",
    }

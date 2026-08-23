from app.config import Settings
from app.index_registry import IndexAliasRegistry


def test_index_alias_activation_and_rollback_are_reversible(tmp_path):
    settings = Settings(data_dir=str(tmp_path), collection_name="dense-a", sparse_collection_name="sparse-a")
    registry = IndexAliasRegistry(settings)
    active = registry.activate("dense-b", "sparse-b", reason="test")
    assert active["active_collection"] == "dense-b"
    rolled = registry.rollback()
    assert rolled["active_collection"] == "dense-a"
    assert rolled["active_sparse_collection"] == "sparse-a"

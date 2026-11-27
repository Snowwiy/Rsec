import pytest

from rsec.artifacts import local_artifacts, verify_export
from rsec.errors import RsecError
from rsec.train import verify_checkpoint
from rsec.utils import sha256, write_json


def test_pickle_only_adapter_rejected_without_deserialization(tmp_path):
    (tmp_path / "adapter_model.bin").write_bytes(b"not executed")
    with pytest.raises(RsecError, match="Safetensors"):
        local_artifacts(tmp_path, adapter=True)


def test_adapter_and_export_inventory_guards(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"header validation is a separate export test")
    with pytest.raises(RsecError, match="adapter_model"):
        local_artifacts(tmp_path, adapter=True)
    (tmp_path / "adapter_model.safetensors").write_bytes(b"fixture")
    write_json(
        tmp_path / "adapter_config.json", {"peft_type": "PROMPT_TUNING", "task_type": "CAUSAL_LM"}
    )
    with pytest.raises(RsecError, match="LoRA"):
        local_artifacts(tmp_path, adapter=True)
    write_json(tmp_path / "export_manifest.json", {"files": {}})
    with pytest.raises(RsecError, match="unmanifested"):
        verify_export(tmp_path)


def test_checkpoint_requires_full_state_and_exact_inventory(tmp_path):
    write_json(tmp_path / "rsec_checkpoint.json", {"signature": "expected", "files": {}})
    with pytest.raises(RsecError, match="signature"):
        verify_checkpoint(tmp_path, "different")
    with pytest.raises(RsecError, match="optimizer"):
        verify_checkpoint(tmp_path, "expected")
    for name in ["optimizer.pt", "scheduler.pt", "trainer_state.json"]:
        (tmp_path / name).write_text("trusted-local fixture only")
    files = {
        n: sha256(tmp_path / n) for n in ["optimizer.pt", "scheduler.pt", "trainer_state.json"]
    }
    write_json(
        tmp_path / "rsec_checkpoint.json", {"signature": "expected", "files": files}, overwrite=True
    )
    assert verify_checkpoint(tmp_path, "expected") == str(tmp_path.resolve())
    (tmp_path / "rng_state.pth").write_text("unmanifested")
    with pytest.raises(RsecError, match="unmanifested"):
        verify_checkpoint(tmp_path, "expected")

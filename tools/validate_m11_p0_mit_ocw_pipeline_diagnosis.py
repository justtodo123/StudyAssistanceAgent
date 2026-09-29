from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_mit_ocw_pipeline_diagnosis import (  # noqa: E402
    MitOcwPipelineDiagnosisError,
    validate_mit_ocw_pipeline_diagnosis,
)

MANIFEST = ROOT / "data/manifests/m11-p0-mit-ocw-pipeline-diagnosis-v1.json"
MATERIALIZATION = ROOT / "data/manifests/m11-p0-mit-ocw-candidate-materialization-v1.json"
DIGEST_EVIDENCE = ROOT / "data/manifests/m11-p0-digest-evidence-v1.json"
RECEIPTS = ROOT / "data/manifests/m11-p0-acquisition-26-receipts-v1.json"


def main() -> int:
    try:
        result = validate_mit_ocw_pipeline_diagnosis(
            json.loads(MANIFEST.read_text(encoding="utf-8")),
            materialization=json.loads(MATERIALIZATION.read_text(encoding="utf-8")),
            digest_evidence=json.loads(DIGEST_EVIDENCE.read_text(encoding="utf-8")),
            receipt_batch=json.loads(RECEIPTS.read_text(encoding="utf-8")),
        )
    except (OSError, TypeError, json.JSONDecodeError, MitOcwPipelineDiagnosisError) as exc:
        print(f"invalid: {exc}")
        return 1
    print("valid: 2 MIT OCW pipeline rejections remain UNRESOLVED; probes are bounded observations only; dependencies sealed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

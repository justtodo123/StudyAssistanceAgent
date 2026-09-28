"""Validate the metadata-only RFC content-quality sampling checkpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
if str(PLATFORM) not in sys.path:
    sys.path.insert(0, str(PLATFORM))

from app.m11_rfc_content_quality_sampling import (  # noqa: E402
    RfcContentQualitySamplingError,
    validate_rfc_content_quality_sampling,
    validate_rfc_content_quality_sampling_result,
)

MANIFEST = ROOT / "data/manifests/m11-p0-rfc-content-quality-sampling-v1.json"
RESULT = ROOT / "data/manifests/m11-p0-rfc-content-quality-sampling-result-v1.json"


def main() -> int:
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        validated = validate_rfc_content_quality_sampling(payload)
        result = validate_rfc_content_quality_sampling_result(
            json.loads(RESULT.read_text(encoding="utf-8"))
        )
    except (OSError, TypeError, json.JSONDecodeError, RfcContentQualitySamplingError) as exc:
        print(f"invalid: {exc}")
        return 1
    print(
        f"valid: {validated['validated_candidate_artifact_count']} RFC candidates / "
        f"{validated['candidate_chunk_count']} chunks sampled as metadata; "
        f"technical_sampling={result['technical_sampling_status']}; "
        "content_quality remains PENDING; Gate 0 unexecuted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

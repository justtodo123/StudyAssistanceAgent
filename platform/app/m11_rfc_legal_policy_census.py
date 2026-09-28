from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NoReturn

SOURCE_ID = "rfc-editor-index"
ASSETS = ("rfc1034", "rfc9110", "rfc9293")
SCOPE_DIGEST = "e405e8d274c3a6a91d1bfa5aa732482ddb100d347af87131aebdbb5439972419"
ROBOTS_DIGEST = "df052cf390448ea2916ce4d3b5f6e42880cd246ea2bf1d5efce5596b1b2e3827"
ROBOTS_POLICY = "candidate-paths-not-disallowed"
EXPECTED_FAMILIES = {"rfc1034": "pre-trust-unlimited-distribution", "rfc9110": "modern-ietf-trust-bcp78", "rfc9293": "modern-ietf-trust-bcp78"}
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class RfcLegalPolicyCensusError(ValueError):
    """The RFC legal-policy census is invalid."""


def _fail(code: str) -> NoReturn:
    raise RfcLegalPolicyCensusError(code)


def census_rfc_legal_policy(*, raw_root: Path) -> dict[str, Any]:
    """Read exact-three RFC text and return body-free notice facts."""
    records = []
    for asset in ASSETS:
        path = raw_root / f"{asset}.raw"
        if not path.is_file():
            _fail("RFC_LEGAL_RAW_MISSING")
        data = path.read_bytes()
        text = data.decode("utf-8", errors="strict")
        if not text.strip():
            _fail("RFC_LEGAL_RAW_EMPTY")
        modern = "IETF Trust" in text and "BCP 78" in text
        unlimited = "Distribution of this memo is unlimited" in text
        family = "modern-ietf-trust-bcp78" if modern else "pre-trust-unlimited-distribution" if unlimited else "unclassified"
        if family != EXPECTED_FAMILIES[asset]:
            _fail("RFC_LEGAL_NOTICE_FAMILY_INVALID")
        year_match = re.search(r"Copyright \(c\) (\d{4}) IETF Trust", text)
        records.append({
            "asset_id": asset,
            "raw_sha256": hashlib.sha256(data).hexdigest(),
            "notice_family": family,
            "copyright_notice_present": year_match is not None,
            "copyright_year": int(year_match.group(1)) if year_match else None,
            "bcp78_present": "BCP 78" in text,
            "trust_legal_provisions_url_present": "trustee.ietf.org/license-info" in text,
            "code_components_bsd_clause_present": "Revised BSD License" in text,
            "pre2008_modification_clause_present": "material from IETF Documents published or made publicly available before November 10, 2008" in text,
            "distribution_unlimited_present": unlimited,
            "robots_digest": ROBOTS_DIGEST,
            "robots_policy": ROBOTS_POLICY,
            "license_status": "PENDING",
            "robots_terms_status": "PENDING",
            "notice_ipr_status": "PENDING",
        })
    return {"technical_census_status": "VERIFIED", "sample_size": 3, "mode": "census", "records": records}


def validate_rfc_legal_policy_census(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {"schema", "census_id", "generated_at", "source_id", "asset_ids", "scope_digest", "technical_census_status", "sample_size", "mode", "records", "authority_issued", "network_used", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included"}
    if not isinstance(payload, Mapping) or set(payload) != required:
        _fail("RFC_LEGAL_FIELDS_INVALID")
    if payload["schema"] != "sa.m11.p0.rfc-legal-policy-census.v1" or payload["source_id"] != SOURCE_ID or payload["asset_ids"] != list(ASSETS) or payload["scope_digest"] != SCOPE_DIGEST:
        _fail("RFC_LEGAL_IDENTITY_INVALID")
    if payload["technical_census_status"] != "VERIFIED" or payload["sample_size"] != 3 or payload["mode"] != "census":
        _fail("RFC_LEGAL_STATUS_INVALID")
    if any(payload[field] is not False for field in ("authority_issued", "network_used", "formal_gate0_executed", "candidate_approval_granted", "publication_authorized", "source_expansion", "lifecycle_mutation", "host_paths_included", "bodies_included")):
        _fail("RFC_LEGAL_ESCALATION_FORBIDDEN")
    records = payload["records"]
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or len(records) != 3:
        _fail("RFC_LEGAL_RECORDS_INVALID")
    seen = set()
    for record in records:
        if not isinstance(record, Mapping) or record.get("asset_id") not in ASSETS or record["asset_id"] in seen:
            _fail("RFC_LEGAL_RECORD_SCOPE_INVALID")
        seen.add(record["asset_id"])
        if record.get("notice_family") != EXPECTED_FAMILIES[record["asset_id"]] or record.get("robots_digest") != ROBOTS_DIGEST or record.get("robots_policy") != ROBOTS_POLICY:
            _fail("RFC_LEGAL_FACTS_INVALID")
        if not isinstance(record.get("raw_sha256"), str) or not _HEX.fullmatch(record["raw_sha256"]):
            _fail("RFC_LEGAL_DIGEST_INVALID")
        if any(record.get(field) != "PENDING" for field in ("license_status", "robots_terms_status", "notice_ipr_status")):
            _fail("RFC_LEGAL_CELLS_MUST_REMAIN_PENDING")
        if record["asset_id"] == "rfc1034":
            if record.get("copyright_notice_present") is not False or record.get("copyright_year") is not None or record.get("distribution_unlimited_present") is not True:
                _fail("RFC_LEGAL_PRETRUST_FACTS_INVALID")
        else:
            if record.get("copyright_notice_present") is not True or record.get("copyright_year") != 2022 or record.get("bcp78_present") is not True or record.get("trust_legal_provisions_url_present") is not True:
                _fail("RFC_LEGAL_MODERN_FACTS_INVALID")
    if seen != set(ASSETS):
        _fail("RFC_LEGAL_RECORD_SCOPE_INVALID")
    return copy.deepcopy(dict(payload))

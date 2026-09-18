# M8 Network Acquisition Authority — Builder Self-Check and Handoff

- cycle: `m8-s1-network-acquisition-cycle-20260918-r01`
- status: `CANDIDATE_FOR_INDEPENDENT_REVIEW_NOT_ACQUISITION_AUTHORITY`
- acquisition: `NOT_AUTHORIZED`
- allowed next action: independent read-only review only

## Scope

This handoff binds the observer policy-validator candidate and its hermetic test. It does not authorize network access, wheel download, wheelhouse creation, resolver execution, installation, formal environment creation, S1 retry, S1-B, S2, S3, or backend selection.

## Builder checks

- observer test command: `D:/Python/python.exe -I tools/m8_test_observe_network_acquisition_v1.py`
- result: `PASS: 21 network-acquisition observer fail-closed controls`
- network access during test: none
- formal wheelhouse created: false
- resolver run: false
- installation run: false
- formal environment created: false
- historical P1 validator: `88/88 PASS` (historical materials only)
- historical P0-r02 validator: `77/77 PASS` (historical materials only)
- `git diff --check`: pass for current candidate changes
- authority JSON parse: pass
- canonical output: UTF-8, no BOM, no CR, final LF

## Candidate bindings

- `tools/m8_observe_network_acquisition_v1.py`
  - SHA-256: `feab03d1e21d92219a0322728ac7241e0e495ec7e922aef8acb17fd7a59f08c2`
  - current content-derived blob: `09d6cfb0da4840541aa2b65aa95467b153556e6d`
- `tools/m8_test_observe_network_acquisition_v1.py`
  - SHA-256: `782b4593a663def125fd4ac17ca58b894d7c54f4903bc4294e8b4f184243345d`
  - current content-derived blob: `095d1aef0c7113234c7f5bebb1ab4d0bdd7a097c`
- observer authority candidate:
  `docs/plans/references/external-artifacts/m8-minimal-1k-v3-s1-network-acquisition-observer-authority-20260918-r02.json`

## Review limitations

The implementation validates declared events only. It is not a real network, write, process, or redaction collector. The exact curl executable remains observed but is not yet independently verified by path-byte binding. These limitations are intentionally fail-closed and must be reviewed before any Owner acquisition decision.

## Repository boundary

Pre-existing unrelated worktree content remains excluded: old resolver candidates, `.claude/tmp/`, and the prior `tools/README.md` modification. No historical decision or failed-closed record was modified.

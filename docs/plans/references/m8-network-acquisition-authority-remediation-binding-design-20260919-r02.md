# M8 Network-Acquisition Remediation Binding Design r02

record_type: M8_NETWORK_ACQUISITION_REMEDIATION_BINDING_DESIGN
cycle_id: m8-network-acquisition-authority-remediation-20260919-r02
cycle_type: NETWORK_ACQUISITION_CYCLE

## Purpose

This is a new remediation cycle. The r01 remediation materials and every earlier M8
record remain immutable historical evidence. This cycle does not amend, rename, or
reuse those materials.

The cycle prepares and requests an independent read-only scope review only. It does
not authorize network access, PyPI access, wheel download, wheelhouse creation,
resolver, installation, formal environment or identity creation, collector execution,
backend selection, S1, S1-B, S2, S3, or any M8 execution.

## Binding contract

The repository objects are frozen in the following one-way stages:

1. `design` records this protocol and cycle identity.
2. `payload` contains the canonical authority-policy bytes and no future Git facts.
3. `payload-binding` records the concrete facts of `design` and `payload`.
4. `candidate` is an envelope that directly freezes the concrete payload and
   payload-binding facts. Its payload digest means the authority payload digest.
5. `candidate-binding` directly freezes the concrete candidate envelope facts and
   all preceding facts.
6. `review-target` freezes the candidate, bindings, Builder self-check, and minimal
   navigation additions in one exact commit.
7. `dispatch-material` freezes the request and prompt, both of which directly name
   the exact review-target commit and preceding object facts.
8. `dispatch` freezes a manifest that directly names every earlier stage.

Every reference points to an already-frozen earlier object. A record never claims its
own resulting Git object identity. This is the ordinary Git object-identity boundary:
the complete commit bytes, including tree, parent, metadata, and message, determine
its OID. The OID of a current record is therefore reported from Git externally or by
a later successor record, never inserted as a future value into that record.

## Required fact fields

For each frozen file, later records use its exact repository path, raw byte size,
SHA-256, and Git blob OID. For each frozen commit, later records use its exact OID,
parent OID, tree OID, and commit object size. A later reviewer must read these facts
from the named Git objects and must not infer them from a branch head or worktree.

## Canonical bytes

JSON artifacts use `sa-json-c14n-v1`: recursively sorted object keys, compact JSON
separators, UTF-8 without BOM, no carriage returns, exactly one final LF, finite
numbers only, and strict duplicate-key, surrogate, unknown-field, and type checks.

## Fail-closed boundary

All authorization flags remain false. `m8_status` remains `BLOCKED / NOT_STARTED`.
The only allowed conclusion after Builder checks is either
`REMEDIATION_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW` or
`REMEDIATION_CANDIDATE_BLOCKED`. Builder evidence is not an independent review and
cannot authorize execution.

The declared-event-only observer remains a policy validator reference. No acquisition
event, collector receipt, wheel, preparation root, or execution result is created by
this cycle.

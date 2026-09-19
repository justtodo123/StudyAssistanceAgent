# M8 Network-Acquisition Remediation Independent Scope Review r02

record_type: M8_NETWORK_ACQUISITION_REMEDIATION_INDEPENDENT_SCOPE_REVIEW
cycle_id: m8-network-acquisition-authority-remediation-20260919-r02
reviewed_at_utc: 2026-09-19T08:35:19Z
reviewer_role: independent-scope-reviewer
review_decision: NETWORK_ACQUISITION_SCOPE_APPROVED
review_basis: FIXED_GIT_OBJECTS_AND_RAW_FILE_BYTES_ONLY

## Scope and fixed identities

This independent, read-only review evaluated the final dispatch and its fixed Git-object
chain. Builder conclusions and the Builder self-check were not used as substitutes for
an independent decision.

- dispatch commit: `7c2a231b42c940cb99e830f083ccd087ee42538d`
- dispatch parent: `ec6de9390da8801f4949d43d24f3449e8506cc67`
- dispatch tree: `48b65e335ce1437ae5fef3e97143cdac38c6aa03`
- dispatch commit object size: `314`
- dispatch-material commit: `ec6de9390da8801f4949d43d24f3449e8506cc67`
- dispatch-material parent: `0153653244a5a6aafc804715b094229fd617a9af`
- dispatch-material tree: `cf93bdd97fcf606d1d429aa03d561a2ccf12fe40`
- dispatch-material commit object size: `309`
- review-target commit: `20d60cd06733c2f42a2ac36434a9d1a41e2eef8d`
- review-target parent: `68b568d097808200ccf55c5904906882f0e1d8f8`
- review-target tree: `8e49fc6c540b9b851c616703f4a290f7e54ecf57`
- review-target commit object size: `316`

## Frozen one-way commit chain

Every commit was resolved directly by OID. Parent, tree, type, and commit object size
matched the declared values.

| Stage | Commit | Parent | Tree | Object bytes |
| --- | --- | --- | --- | ---: |
| design | `075725e523821c577cf042ffd719bfed1ded6959` | `8e7e0b7788184a4a3cf58751f39e70e386cc300b` | `6a5159e379a31d3bdb65485ac3b6aeb7e77d783e` | 310 |
| payload | `44e6cff5535f37405b277a893bc59e9bbb4781c9` | `075725e523821c577cf042ffd719bfed1ded6959` | `fbb513bac44c0652c969bedac2ee765e349b880c` | 314 |
| payload binding | `bbb131c8e0816c3fec28e0e49787ea60f8101724` | `44e6cff5535f37405b277a893bc59e9bbb4781c9` | `a88ab2adb7d7159cc718f3a657dbf90a71df8930` | 304 |
| candidate envelope | `1e4beeeec0690a4c72868625556af68913410bd7` | `bbb131c8e0816c3fec28e0e49787ea60f8101724` | `3879ca8067cc7c0c5c3c57124b8ee1fa51f2c1a4` | 317 |
| candidate binding | `68b568d097808200ccf55c5904906882f0e1d8f8` | `1e4beeeec0690a4c72868625556af68913410bd7` | `ce7cac027c59a05e4e280cf5000051dce1549941` | 306 |
| review target | `20d60cd06733c2f42a2ac36434a9d1a41e2eef8d` | `68b568d097808200ccf55c5904906882f0e1d8f8` | `8e49fc6c540b9b851c616703f4a290f7e54ecf57` | 316 |

The chain is additive and one-way. No self-reference, forward reference, branch-head
inference, sibling-record reconstruction, deferred binding, placeholder binding, or
hidden selection was required. The candidate digest is explicitly the authority-payload
SHA-256; the separately named candidate-envelope digest is the candidate-envelope file
SHA-256.

## Recomputed file facts

| Material | Bytes | SHA-256 | Git blob |
| --- | ---: | --- | --- |
| final dispatch manifest | 5149 | `47202952dc611bb5b5dd9a0f2210891defe7ad8b56fdfe6c1eea3f0e17d6faf6` | `05988762b8458918b077b5450c847775785c5bc5` |
| review request | 5801 | `b8fba34f1c437290578f0d4bc3cd2fb5c50be2cf7d70f877c132ec4e659c69f8` | `c5fdda5843e8876f739a2ae8d69cfdff7fca6b68` |
| review prompt | 6488 | `0bce61e46c8df365e56abe7b78d6883e1f56d9309d43fd024055a516607441a9` | `ea096bbe709a7e3e3b2157d32711fa08afcf1d3e` |
| binding design | 3219 | `501c9c57a37ef3f93bd0ba40aae4ca0911bdfb2eb54ecc8de727e6f1beaa6403` | `a3c5865965015464da2d26e58fdaabfaf5ad21cc` |
| historical r01 failure | 1610 | `303fcfec5a30e18543a10b94e692bacdd766369fc7c086a2f19d8ca69d8be252` | `6aed5b3f636e247efbbfb7b47149a1e7792fc968` |
| authority payload | 12245 | `f2992204cff95bf56c85601f44cf47ec03f0655aa71fe4690f199fd864da8a1e` | `a5b0e2f92bc16092738f57bf2329394d1694fe90` |
| payload binding | 1712 | `1b3a9f6bad93ba15f0a36cbcb45c14e27d759b2525e517e5a04c1ab48f80c7c3` | `c67469440360332d37f2b3b3400182cb4f1e3bc5` |
| candidate envelope | 2614 | `0ebe9bf8a335e3f6bcde7e6791311370e2104cd80361de3dda1757f5b6bf5332` | `c4478c841b74d3aec8038677686f5d6fdad0a2d5` |
| candidate binding | 2575 | `479d6bf79592d5f1527012c86795313f866714d5ab0c881db9d5dc5c2876f4d4` | `ec82b25d3ec69ab8f6e6e78ff57652c03ed3b3db` |
| Builder self-check | 3894 | `55235762378b66383a6a17edfc01eeff8604cae557cd9425f3018ac907f6a32d` | `d3f95d3b0fd2b39fb73df3c933d3cf92d787bea1` |
| target references navigation | 68641 | `746529624269c131d3508d718f6095628ab6b87e55e2354063c9f08724f89304` | `6b630fd0dde716d59a8b87fa96bbc6061cfb4362` |

All expected values matched the bytes read from the exact named Git objects. The r01
failure record remained unchanged in the frozen chain and was treated as immutable
historical evidence.

## Canonical JSON and document validation

The authority payload, payload binding, candidate envelope, candidate binding, and final
dispatch manifest passed `sa-json-c14n-v1` byte comparison:

- recursively sorted object keys and compact separators: pass
- UTF-8 without BOM: pass
- no carriage return and exactly one final LF: pass
- duplicate object keys rejected: pass
- non-finite numbers rejected: pass
- Unicode surrogates rejected: pass
- missing and unknown fields fail closed: pass
- strict boolean/integer distinction and exact integer bounds: pass
- canonical serialization reproduced the raw Git-object bytes: pass

## Policy, limits, and provenance

The payload closes the declared authority policy without granting execution:

- official PyPI strict mode, HTTPS and GET only, fixed initial/redirect hosts, TLS
  verification required, proxy/mirror/authentication/certificate bypass denied: pass
- fixed absolute downloader identity, SHA-256, version, TLS backend, argument allowlist,
  empty explicit environment, closed stdin, no shell, and bounded supervisor behavior:
  pass as candidate policy identity; not treated as an executed downloader receipt
- wheel-only policy; sdist, source archive/build, setup.py, editable, VCS, dependency
  closure, resolver expansion, and candidate-code execution denied: pass
- write root and persistent relative allowlist, path-escape/reparse/ADS/device-name
  controls, partial handling, verify-before-publish, same-directory atomic rename, and
  existing-target denial: pass
- concurrency `1`, connect timeout `15`, request/total timeout `300`, redirect limit `3`,
  retry count `1`, maximum attempts `2`, maximum files `256`, metadata bytes `4194304`,
  single-wheel bytes `536870912`, total-wheel bytes `2147483648`, and resolver/dependency
  expansion `0`: pass
- provenance schema explicitly requires source, URL/redirect/TLS/HTTP, package/version,
  wheel tags/size/hash, downloader, authority/candidate/binding, timestamp, validation,
  dependency, and failure/stop facts; unknown or missing fields fail closed: pass
- `no_real_provenance_in_candidate: true` is correct because no acquisition occurred;
  no acquisition evidence was fabricated: pass
- current-candidate exact downloader validation and real collector coverage receipts
  remain prerequisites for any later acquisition authorization; they are not represented
  as completed and do not invalidate this policy-only scope decision: pass

## Authorization and execution boundary

The following remain explicitly false: acquisition, network access, PyPI access, wheel
download, wheelhouse creation, resolver, installation, formal venv, formal identity,
real collector, backend selection, S1 retry, S1-B, S2, and S3 authorization.

No network or PyPI access, download, wheelhouse/preparation-root creation, pip, resolver,
installation, formal environment/identity creation, backend selection, collector, S1,
S1-B, S2, S3, or other M8 execution was performed during this review.

`m8_status` remains `BLOCKED / NOT_STARTED`. This approval closes only the independent
scope review of the frozen policy package. It does not grant acquisition or execution
authority and does not satisfy any later owner, collector, provenance, or execution gate.

## Decision

`NETWORK_ACQUISITION_SCOPE_APPROVED`

Approval basis: all fixed Git identities, raw file facts, canonical JSON constraints,
direct one-way bindings, strict policy fields, numeric limits, provenance requirements,
authorization states, and historical immutability checks passed without mismatch.

allowed_next_action: `request-owner-review-for-network-acquisition-authorization`

# M8 Network-Acquisition Remediation Independent Scope Review Prompt r02

You are the independent, read-only scope reviewer for cycle
`m8-network-acquisition-authority-remediation-20260919-r02`.

## Fixed review package

Review exactly this frozen review-target commit and no moving branch head:

- review-target commit: `20d60cd06733c2f42a2ac36434a9d1a41e2eef8d`
- review-target parent: `68b568d097808200ccf55c5904906882f0e1d8f8`
- review-target tree: `8e49fc6c540b9b851c616703f4a290f7e54ecf57`
- review-target commit object size: `316`

The review-target must resolve the following already-frozen one-way chain:

- design commit: `075725e523821c577cf042ffd719bfed1ded6959`
- authority payload commit: `44e6cff5535f37405b277a893bc59e9bbb4781c9`
- payload-binding commit: `bbb131c8e0816c3fec28e0e49787ea60f8101724`
- candidate-envelope commit: `1e4beeeec0690a4c72868625556af68913410bd7`
- candidate-binding commit: `68b568d097808200ccf55c5904906882f0e1d8f8`

Exact preceding commit facts:

- design: parent `8e7e0b7788184a4a3cf58751f39e70e386cc300b`, tree `6a5159e379a31d3bdb65485ac3b6aeb7e77d783e`, object size `310`
- authority payload: parent `075725e523821c577cf042ffd719bfed1ded6959`, tree `fbb513bac44c0652c969bedac2ee765e349b880c`, object size `314`
- payload-binding: parent `44e6cff5535f37405b277a893bc59e9bbb4781c9`, tree `a88ab2adb7d7159cc718f3a657dbf90a71df8930`, object size `304`
- candidate-envelope: parent `bbb131c8e0816c3fec28e0e49787ea60f8101724`, tree `3879ca8067cc7c0c5c3c57124b8ee1fa51f2c1a4`, object size `317`
- candidate-binding: parent `1e4beeeec0690a4c72868625556af68913410bd7`, tree `ce7cac027c59a05e4e280cf5000051dce1549941`, object size `306`

Exact file facts:

- design path `docs/plans/references/m8-network-acquisition-authority-remediation-binding-design-20260919-r02.md`, bytes `3219`, SHA-256 `501c9c57a37ef3f93bd0ba40aae4ca0911bdfb2eb54ecc8de727e6f1beaa6403`, Git blob `a3c5865965015464da2d26e58fdaabfaf5ad21cc`
- historical r01 failure path `docs/plans/references/m8-network-acquisition-authority-remediation-independent-review-failure-20260919-r01.md`, bytes `1610`, SHA-256 `303fcfec5a30e18543a10b94e692bacdd766369fc7c086a2f19d8ca69d8be252`, Git blob `6aed5b3f636e247efbbfb7b47149a1e7792fc968`
- authority payload path `docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-payload-20260919-r02.json`, bytes `12245`, SHA-256 `f2992204cff95bf56c85601f44cf47ec03f0655aa71fe4690f199fd864da8a1e`, Git blob `a5b0e2f92bc16092738f57bf2329394d1694fe90`
- payload-binding path `docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-payload-binding-20260919-r02.json`, bytes `1712`, SHA-256 `1b3a9f6bad93ba15f0a36cbcb45c14e27d759b2525e517e5a04c1ab48f80c7c3`, Git blob `c67469440360332d37f2b3b3400182cb4f1e3bc5`
- candidate-binding path `docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-candidate-binding-20260919-r02.json`, bytes `2575`, SHA-256 `479d6bf79592d5f1527012c86795313f866714d5ab0c881db9d5dc5c2876f4d4`, Git blob `ec82b25d3ec69ab8f6e6e78ff57652c03ed3b3db`
- candidate path `docs/plans/references/external-artifacts/m8-network-acquisition-authority-remediation-candidate-20260919-r02.json`, bytes `2614`, SHA-256 `0ebe9bf8a335e3f6bcde7e6791311370e2104cd80361de3dda1757f5b6bf5332`, Git blob `c4478c841b74d3aec8038677686f5d6fdad0a2d5`



- raw bytes: `12245`
- SHA-256: `f2992204cff95bf56c85601f44cf47ec03f0655aa71fe4690f199fd864da8a1e`
- Git blob: `a5b0e2f92bc16092738f57bf2329394d1694fe90`

Required candidate-envelope facts:

- raw bytes: `2614`
- SHA-256: `0ebe9bf8a335e3f6bcde7e6791311370e2104cd80361de3dda1757f5b6bf5332`
- Git blob: `c4478c841b74d3aec8038677686f5d6fdad0a2d5`

Required candidate-binding facts:

- raw bytes: `2575`
- SHA-256: `479d6bf79592d5f1527012c86795313f866714d5ab0c881db9d5dc5c2876f4d4`
- Git blob: `ec82b25d3ec69ab8f6e6e78ff57652c03ed3b3db`

## Review method

Read only the exact Git objects named above and the files reachable in the fixed
review-target commit. Recompute raw file sizes, SHA-256 digests, Git blob IDs, commit
parents, trees, and commit object sizes. Verify that every later record directly names
all required facts of every earlier record. Verify that the chain is one-way and closed:
no forward reference, branch-head inference, sibling-record reconstruction, deferred
binding, self-reference, ambiguous digest semantics, placeholder, or hidden selection
is acceptable.

For JSON artifacts, verify `sa-json-c14n-v1`: recursively sorted object keys, compact
separators, UTF-8 without BOM, no carriage return, exactly one final LF, finite numbers,
rejected duplicate keys, rejected surrogates, strict unknown-field checks, and strict
boolean/integer typing. Verify all source, runtime, downloader, write, provenance,
failure, network, package, path-safety, retry, timeout, bytecode, locale, timezone,
preparation-root, allowlist, partial/atomic, and numeric-limit policy fields. Verify the
candidate digest explicitly means the authority-payload SHA-256, while the candidate
binding separately means the candidate-envelope file SHA-256.

Treat the Builder self-check as construction evidence only. It cannot substitute for an
independent decision. Treat all r01 and earlier materials as immutable historical
references; any drift or modification is a rejection.

## Execution prohibitions

Do not access the network or PyPI. Do not download or copy wheels, create a wheelhouse
or preparation root, invoke a resolver, pip, installer, formal virtual environment or
identity, select a backend, run a collector, or execute S1, S1-B, S2, S3, or any M8
execution. Do not create acquisition evidence. Do not alter repository files or Git
history.

The following authorization boundary must remain false and non-executing:

- acquisition, network access, PyPI access, wheel download, wheelhouse creation
- resolver, installation, formal venv, formal identity
- real collector, backend selection, S1 retry, S1-B, S2, S3

`m8_status` must remain `BLOCKED / NOT_STARTED`.

## Decision

Return only one of these final decisions:

- `REMEDIATION_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW` if every exact fact and policy
  check passes and the package is ready for the independent review outcome; or
- `REMEDIATION_CANDIDATE_BLOCKED` if any fact, binding, immutability, policy, or
  fail-closed check fails.

This prompt does not grant execution authority and does not constitute an independent
review decision itself.

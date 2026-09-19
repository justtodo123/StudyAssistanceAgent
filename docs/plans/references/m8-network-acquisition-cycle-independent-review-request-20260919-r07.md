# M8 Network-Acquisition Cycle Independent Scope Review Request r07

record_type: M8_NETWORK_ACQUISITION_CYCLE_INDEPENDENT_SCOPE_REVIEW_REQUEST
cycle_id: m8-network-acquisition-authority-20260919-r02
cycle_type: NETWORK_ACQUISITION_CYCLE
candidate_commit: 478d36bcba866838480e115cbcc2050dc9e24d33
candidate_parent: eeb970da227bf77188bd7684028df38a5e755044
candidate_tree: 106b0c8adfb83ab6007faa25eb6c7fedebf631c6
candidate_bytes: 5298
candidate_sha256: a2938f489cae95e221eec8041f80be9ce5290b30403d484eff8a5663f95d16d2
candidate_git_blob: e034e1ef9e0cd09bba7513f06c8336cecfd82d39
candidate_record: external-artifacts/m8-network-acquisition-authority-candidate-20260919-r03.json
builder_self_check: m8-network-acquisition-cycle-builder-self-check-20260919-r03.md
prior_review: m8-network-acquisition-cycle-independent-review-20260919-r06.md
review_scope: corrected canonical authority, concrete source/runtime/write/provenance/limit policy, and closed Git binding
reviewer_id: NOT_YET_DESIGNATED
independence_required: true

reviewer_must_not:
  - access-network
  - download-wheel
  - create-wheelhouse
  - run-resolver
  - install-dependencies
  - execute-s1-s2-s3

requested_decision_values:
  - NETWORK_ACQUISITION_SCOPE_ACCEPTED
  - NETWORK_ACQUISITION_SCOPE_REJECTED_FAILED_CLOSED
  - RETURN_FOR_SCOPE_REMEDIATION

acquisition_authorized: false
network_access_authorized: false
wheel_download_authorized: false
wheelhouse_creation_authorized: false
resolver_authorized: false
installation_authorized: false
s1_retry_authorized: false
s2_authorized: false
s3_authorized: false
backend_selection_authorized: false
m8_status: BLOCKED / NOT_STARTED

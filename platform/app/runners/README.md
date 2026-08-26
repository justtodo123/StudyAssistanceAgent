# M6a runner adapters

- [state_machine.py](state_machine.py) maps the provider-neutral Runner contract to the durable
  StudySessionService state machine.

The adapter delegates create/get/answer operations and derives snapshots from persisted domain
state. It does not create a second runner store, bypass answer progression, or persist request-only
cancel/fail states. The production study-session API continues to call StudySessionService directly.

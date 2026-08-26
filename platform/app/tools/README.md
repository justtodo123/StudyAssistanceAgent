# M6a deterministic tool adapters

This package exposes provider-neutral, directly invoked read-only tools:

- [retrieve.py](retrieve.py) calls the injected retrieval service with the authorized source scope.
- [quiz.py](quiz.py) previews deterministic default-pack quizzes with an invocation-local RNG.
- [review_due.py](review_due.py) reads due reviews without writing review history.
- [common.py](common.py) centralizes exact argument validation, authorization, cancellation, safe
  errors, correlation passthrough, and portable provenance conversion.

There is intentionally no registry, automatic discovery, provider SDK integration, write tool, or
agent turn loop in M6a.

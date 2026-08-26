# M6a source adapters

This package contains read-only adapters for complete Markdown source snapshots.

- [markdown_pack.py](markdown_pack.py) materializes the trusted repository `knowledge/` pack as
  `knowledge-pack`, preserving portable identities and deterministic metadata.
- [static_markdown.py](static_markdown.py) strictly materializes up to three startup-configured
  approved Markdown sources. Invalid content rejects the whole source; non-strict mode may omit
  that complete source but never publishes part of it.

Extra sources use portable `extra://{source_id}/{logical_uri}` provenance. This package does not
register, synchronize, mutate, or delete runtime user sources; those lifecycle responsibilities
remain outside M6a.

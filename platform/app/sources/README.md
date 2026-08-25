# M6a default source adapters

This package contains read-only adapters that expose the repository's trusted default
Markdown knowledge pack through the M6a `Source` contract.

- [markdown_pack.py](markdown_pack.py) materializes `knowledge/` as the `knowledge-pack`
  logical source, with portable identities and deterministic complete-snapshot metadata.

It does not register runtime sources, write user content, or manage source lifecycle; those
responsibilities remain outside M6a-2.

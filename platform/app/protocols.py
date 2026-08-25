"""Provider-neutral contracts for the M6a harness skeleton.

This module intentionally depends only on the Python standard library.  Concrete
services and repositories adapt to these contracts in later M6a slices; the
protocols themselves must not import application implementations.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable

JsonObject = dict[str, Any]

_SOURCE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:([\\/]|$)")


class ProtocolValidationError(ValueError):
    """Raised when a protocol value would violate a stable harness contract."""


def normalize_logical_uri(value: str) -> str:
    """Return a portable relative URI, rejecting host-path representations."""
    if not isinstance(value, str) or not value.strip():
        raise ProtocolValidationError("logical_uri must be a non-empty string")
    uri = unicodedata.normalize("NFC", value).replace("\\", "/")
    if uri.startswith(("/", "//")) or _WINDOWS_DRIVE_RE.match(uri):
        raise ProtocolValidationError("logical_uri must be relative")
    if any(ord(char) < 32 for char in uri):
        raise ProtocolValidationError("logical_uri contains a control character")
    parts = uri.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ProtocolValidationError("logical_uri contains an invalid path segment")
    if not uri.lower().endswith(".md"):
        raise ProtocolValidationError("logical_uri must reference Markdown")
    return uri


def validate_source_id(value: str, *, allow_default: bool = False) -> str:
    """Validate and return a logical source namespace."""
    if not isinstance(value, str) or not _SOURCE_ID_RE.fullmatch(value):
        raise ProtocolValidationError("source_id has an invalid format")
    if value == "knowledge-pack" and allow_default:
        return value
    if value == "knowledge-pack" or value == "crawler-candidates" or value.startswith("user-"):
        raise ProtocolValidationError("source_id is reserved")
    return value


def logical_document_id(source_id: str, logical_uri: str) -> str:
    """Derive the portable 32-hex document identity for a source snapshot."""
    validate_source_id(source_id, allow_default=True)
    uri = normalize_logical_uri(logical_uri)
    return hashlib.sha256(f"{source_id}\0{uri}".encode("utf-8")).hexdigest()[:32]


def logical_chunk_id(
    document_id: str,
    chunk_key: str,
    chunk_schema: str = "sa.chunk.markdown-h2.v1",
) -> str:
    """Derive a stable chunk identity from document, key, and schema version."""
    if not re.fullmatch(r"[0-9a-f]{32}", document_id):
        raise ProtocolValidationError("document_id must be a 32-character hexadecimal digest")
    if not isinstance(chunk_key, str) or not chunk_key:
        raise ProtocolValidationError("chunk_key must be non-empty")
    if not isinstance(chunk_schema, str) or not chunk_schema:
        raise ProtocolValidationError("chunk_schema must be non-empty")
    return hashlib.sha256(
        f"{document_id}\0{chunk_key}\0{chunk_schema}".encode("utf-8")
    ).hexdigest()[:32]


class SourceType(StrEnum):
    HUMAN_MARKDOWN = "human_markdown"
    WEB_REVIEWED = "web_reviewed"


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Stable logical identity independent of a local mount point."""

    source_id: str
    logical_uri: str
    document_id: str = field(init=False)

    def __post_init__(self) -> None:
        validate_source_id(self.source_id, allow_default=True)
        uri = normalize_logical_uri(self.logical_uri)
        object.__setattr__(self, "logical_uri", uri)
        object.__setattr__(self, "document_id", logical_document_id(self.source_id, uri))


@dataclass(frozen=True, slots=True)
class SourceChunk:
    """A source chunk carrying only logical, portable provenance."""

    identity: SourceIdentity
    chunk_key: str
    content: str
    title: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    chunk_schema: str = "sa.chunk.markdown-h2.v1"
    chunk_id: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise ProtocolValidationError("chunk content must be a string")
        object.__setattr__(
            self,
            "chunk_id",
            logical_chunk_id(self.identity.document_id, self.chunk_key, self.chunk_schema),
        )


@dataclass(frozen=True, slots=True)
class SourceDescriptor:
    """Published metadata for one complete source snapshot."""

    source_id: str
    source_type: SourceType
    revision: str
    fingerprint: str
    generation: str

    def __post_init__(self) -> None:
        validate_source_id(self.source_id, allow_default=True)
        for name in ("revision", "fingerprint", "generation"):
            if not getattr(self, name):
                raise ProtocolValidationError(f"{name} must be non-empty")


@runtime_checkable
class Source(Protocol):
    """Read-only source snapshot contract used by retrieval adapters."""

    def describe(self) -> SourceDescriptor:
        ...

    def iter_chunks(self) -> Iterable[SourceChunk]:
        ...


@runtime_checkable
class LearningStateRepository(Protocol):
    """Session and answer state; domain services remain the write authority."""

    def get(self, session_id: str) -> JsonObject | None:
        ...

    def save(self, record: JsonObject) -> None:
        ...


@runtime_checkable
class ReviewRepository(Protocol):
    """Review history and due-item persistence boundary."""

    def get(self, file_key: str) -> JsonObject | None:
        ...

    def save(self, file_key: str, entry: JsonObject) -> JsonObject:
        ...

    def all(self) -> dict[str, JsonObject]:
        ...

    def find_by_source_session(self, session_id: str) -> JsonObject | None:
        ...


@runtime_checkable
class SourceRegistryRepository(Protocol):
    """Reserved M7 persistence boundary; M6a uses startup configuration only."""

    def get(self, source_id: str) -> SourceDescriptor | None:
        ...

    def save(self, descriptor: SourceDescriptor) -> None:
        ...


@runtime_checkable
class RetrievalIndex(Protocol):
    """Read-only search boundary for logical source chunks.

    Existing vector stores retain their native ``RetrievalChunk`` and embedding
    replacement APIs.  An adapter owns conversion into this portable contract.
    """

    @property
    def generation(self) -> str:
        ...

    def search(self, query: str, top_k: int = 5) -> Sequence[SourceChunk]:
        ...


@dataclass(frozen=True, slots=True)
class RetrievalSnapshot:
    """A complete logical retrieval snapshot supplied to an index adapter."""

    generation: str
    chunks: tuple[SourceChunk, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.generation, str) or not self.generation:
            raise ProtocolValidationError("generation must be non-empty")


@runtime_checkable
class RetrievalSnapshotWriter(Protocol):
    """Explicit snapshot-publication boundary; not the legacy vector-store API."""

    def replace_all(self, snapshot: RetrievalSnapshot) -> None:
        ...


def validate_source_snapshot(source: Source) -> SourceDescriptor:
    """Validate that each emitted chunk belongs to the described source."""
    descriptor = source.describe()
    if not isinstance(descriptor, SourceDescriptor):
        raise ProtocolValidationError("source descriptor must be a SourceDescriptor")
    for chunk in source.iter_chunks():
        if not isinstance(chunk, SourceChunk):
            raise ProtocolValidationError("source must emit SourceChunk values")
        if chunk.identity.source_id != descriptor.source_id:
            raise ProtocolValidationError("source chunk namespace must match descriptor")
    return descriptor


class ToolCapability(StrEnum):
    READ = "read"
    WRITE = "write"


class SideEffect(StrEnum):
    NONE = "none"
    DOMAIN_WRITE = "domain_write"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Machine-readable tool metadata; arguments are described by JSON Schema."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    capability: ToolCapability = ToolCapability.READ
    side_effect: SideEffect = SideEffect.NONE
    idempotent: bool = True

    def __post_init__(self) -> None:
        if not self.name or not self.name.replace("_", "").isalnum():
            raise ProtocolValidationError("tool name must be a simple identifier")
        if not isinstance(self.description, str) or not self.description:
            raise ProtocolValidationError("tool description must be non-empty")
        if not isinstance(self.input_schema, Mapping):
            raise ProtocolValidationError("tool input_schema must be a JSON object")
        try:
            encoded_schema = json.dumps(self.input_schema, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ProtocolValidationError("tool input_schema must be JSON-serializable") from exc
        if not isinstance(json.loads(encoded_schema), dict):
            raise ProtocolValidationError("tool input_schema must be a JSON object")
        if self.input_schema.get("type") != "object":
            raise ProtocolValidationError("tool input_schema must describe an object")
        if self.capability is ToolCapability.READ and self.side_effect is not SideEffect.NONE:
            raise ProtocolValidationError("read tools cannot declare domain side effects")
        if self.capability is ToolCapability.WRITE and self.side_effect is SideEffect.NONE:
            raise ProtocolValidationError("write tools must declare a side effect")


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Authorization and request metadata passed to one tool invocation."""

    learner_id: str | None
    source_scope: str
    correlation_id: str
    permissions: frozenset[str] = frozenset()
    cancelled: bool = False
    budget: Mapping[str, int] = field(default_factory=dict)

    def allows(self, spec: ToolSpec) -> bool:
        """Return whether this context authorizes a non-cancelled capability call."""
        if self.cancelled or not self.correlation_id or not self.source_scope:
            return False
        required = "read" if spec.capability is ToolCapability.READ else "write"
        return required in self.permissions


@dataclass(frozen=True, slots=True)
class ToolError:
    """Safe structured error; raw provider or filesystem exceptions do not belong here."""

    code: str
    message: str
    retryable: bool = False

    def __post_init__(self) -> None:
        if not self.code or not self.message:
            raise ProtocolValidationError("tool error code and message are required")


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Structured tool response with explicit capability and failure semantics."""

    data: Any = None
    sources: tuple[SourceIdentity, ...] = ()
    error: ToolError | None = None
    side_effect: SideEffect = SideEffect.NONE
    correlation_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.error is None


@runtime_checkable
class Tool(Protocol):
    """Tool execution boundary; implementations remain responsible for authorization."""

    @property
    def spec(self) -> ToolSpec:
        ...

    def execute(self, context: ToolContext, arguments: Mapping[str, Any]) -> ToolResult:
        ...


class RunnerStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class RunnerContext:
    """Request metadata; correlation IDs trace calls and never identify runs."""

    learner_id: str | None
    correlation_id: str = field(default_factory=lambda: secrets.token_hex(16))
    permissions: frozenset[str] = frozenset()
    cancelled: bool = False


class RunnerEventType(StrEnum):
    """Minimal control events accepted by the non-autonomous M6a runner boundary."""

    CONTINUE = "continue"
    COMPLETE = "complete"
    CANCEL = "cancel"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class RunnerEvent:
    """A typed control event supplied to a runner step."""

    type: RunnerEventType
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RunnerSnapshot:
    """Serializable control state, deliberately separate from domain session state."""

    run_id: str
    status: RunnerStatus
    revision: int = 0
    waiting_for: str | None = None
    state: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ProtocolValidationError("run_id must be non-empty")
        if self.revision < 0:
            raise ProtocolValidationError("runner revision cannot be negative")


@dataclass(frozen=True, slots=True)
class RunnerResult:
    """Result of a lifecycle operation, including the next control snapshot."""

    snapshot: RunnerSnapshot
    output: Any = None
    error: ToolError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@runtime_checkable
class Runner(Protocol):
    """Cross-request lifecycle contract with durable run and terminal semantics."""

    def start(self, context: RunnerContext) -> RunnerResult:
        ...

    def get(self, context: RunnerContext, run_id: str) -> RunnerResult:
        ...

    def resume(self, context: RunnerContext, run_id: str) -> RunnerResult:
        ...

    def step(self, context: RunnerContext, run_id: str, event: RunnerEvent) -> RunnerResult:
        ...

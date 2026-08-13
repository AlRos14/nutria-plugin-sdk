"""Typed resource and capability contracts for Nutria plugin manifests."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


_RESOURCE_TYPE_PATTERN = r"^[a-z][a-z0-9_.-]{0,127}$"


class CapabilityEffect(str, Enum):
    READ = "read"
    PREPARE = "prepare"
    WRITE = "write"
    EXTERNAL_WRITE = "external_write"


class CapabilityExposure(str, Enum):
    """Who may invoke a graph-visible capability."""

    MODEL = "model"
    HOST = "host"
    ADMIN = "admin"


class NonCallableReason(BaseModel):
    """Safe explanation for a graph-visible capability that the model cannot load."""

    code: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    safe_summary: str = Field(..., min_length=1, max_length=500)

    model_config = {"extra": "forbid"}


class PreparedActionDescriptor(BaseModel):
    """Portable exact-preview contract used by every Nutria host."""

    preview_argument: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    preview_value: Any
    execute_value: Any
    ttl_seconds: int = Field(..., ge=60, le=86_400)

    model_config = {"extra": "forbid"}


class IdempotencyDescriptor(BaseModel):
    """Execution idempotency contract for a capability."""

    argument_name: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    required_for_execution: bool

    model_config = {"extra": "forbid"}


class CompletionDescriptor(BaseModel):
    """Authoritative receipt kinds required before a capability is complete."""

    receipts: list[str] = Field(..., min_length=1)

    model_config = {"extra": "forbid"}

    @field_validator("receipts")
    @classmethod
    def _validate_receipts(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not cleaned:
            raise ValueError("completion receipts must not be empty")
        for receipt in cleaned:
            import re

            if not re.fullmatch(r"^[a-z][a-z0-9_.-]{0,127}$", receipt):
                raise ValueError("completion receipts must be stable lowercase identifiers")
        return cleaned


class ResourceType(str, Enum):
    TENANT = "tenant"
    CLIENT = "client"
    BRAND = "brand"
    AGENT = "agent"
    SERVICE_PRINCIPAL = "service_principal"
    HUMAN_ACTOR = "human_actor"
    CUSTOMER_SESSION = "customer_session"
    CONNECTOR = "connector"
    TEAM = "team"
    AUTHORITY_GRANT = "authority_grant"
    CONVERSATION = "conversation"
    CHANNEL_CONVERSATION = "channel_conversation"
    MESSAGE = "message"
    CHANNEL_EVENT = "channel_event"
    ATTACHMENT = "attachment"
    CASE = "case"
    ORDER = "order"
    PREPARED_ACTION = "prepared_action"
    OPERATION = "operation"
    RESPONSE = "response"
    ARTIFACT = "artifact"
    CAPABILITY = "capability"
    CUSTOMER = "customer"
    EMAIL_THREAD = "email_thread"
    EMAIL_MESSAGE = "email_message"
    WHATSAPP_CHAT = "whatsapp_chat"
    WHATSAPP_MESSAGE = "whatsapp_message"
    WHATSAPP_ATTACHMENT = "whatsapp_attachment"
    PRODUCT = "product"
    FILE = "file"
    TASK = "task"
    TRELLO_BOARD = "trello_board"
    TRELLO_CARD = "trello_card"
    TRELLO_LABEL = "trello_label"
    MRW_SHIPMENT = "mrw_shipment"
    MRW_LABEL = "mrw_label"


class CapabilityRequirement(BaseModel):
    """Runtime requirement evaluated by the host before exposing a capability."""

    authority: Literal["read", "write_internal", "write_external"]
    audience: list[str] = Field(..., min_length=1)
    task_context: Literal["optional", "required"]

    model_config = {"extra": "forbid"}

    @field_validator("audience")
    @classmethod
    def _validate_audience(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class ResourceBinding(BaseModel):
    """A resource consumed or produced by a capability."""

    name: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    resource_type: ResourceType | str
    required: bool = True
    many: bool = False

    model_config = {"extra": "forbid"}

    @field_validator("resource_type")
    @classmethod
    def _validate_resource_type(cls, value: ResourceType | str) -> ResourceType | str:
        _validate_resource_type_id(value)
        return value


class CapabilityInputBinding(BaseModel):
    """Maps a typed value or world resource to one plugin argument."""

    kind: Literal["value", "resource"]
    semantic_field: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    argument_name: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    resource_type: ResourceType | str | None = None
    required: bool = True
    sensitivity: Literal["safe", "personal"] = "safe"
    accepted_origins: list[Literal["current_user", "world_resource"]] = Field(min_length=1)

    model_config = {"extra": "forbid"}

    @field_validator("resource_type")
    @classmethod
    def _validate_resource_type(cls, value: ResourceType | str | None) -> ResourceType | str | None:
        if value is not None:
            _validate_resource_type_id(value)
        return value

    @model_validator(mode="after")
    def _validate_kind(self) -> "CapabilityInputBinding":
        if self.kind == "resource" and self.resource_type is None:
            raise ValueError("resource inputs require resource_type")
        if self.kind == "value" and self.resource_type is not None:
            raise ValueError("value inputs must not declare resource_type")
        if self.sensitivity == "personal" and "current_user" not in self.accepted_origins:
            raise ValueError("personal inputs must accept current_user evidence")
        return self


class CapabilityOutputBinding(BaseModel):
    """Maps one plugin result field to a typed resource output."""

    result_path: str = Field(..., pattern=r"^\$?(?:\.[a-zA-Z][a-zA-Z0-9_-]*)+$")
    resource_type: ResourceType | str
    output_name: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    many: bool = False

    model_config = {"extra": "forbid"}

    @field_validator("resource_type")
    @classmethod
    def _validate_resource_type(cls, value: ResourceType | str) -> ResourceType | str:
        _validate_resource_type_id(value)
        return value


def _validate_resource_type_id(value: ResourceType | str) -> None:
    import re

    raw = value.value if isinstance(value, ResourceType) else str(value)
    if not re.fullmatch(_RESOURCE_TYPE_PATTERN, raw):
        raise ValueError("resource type must be a stable lowercase identifier")


class WorldProjectionDescriptor(BaseModel):
    """Named provider projection; payload fields remain provider-owned."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=1_000)
    fields: list[str] = Field(default_factory=list, max_length=64)
    sensitivity: str = Field(default="safe", pattern=r"^(safe|authorized)$")

    model_config = {"extra": "forbid"}


class ResourceTypeDescriptor(BaseModel):
    """How one provider exposes a stable resource namespace to the world."""

    id: ResourceType | str
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=2_000)
    identity_fields: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    version_field: str | None = Field(default=None, max_length=128)
    search_capability: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    inspect_capability: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    ttl_seconds: int = Field(default=300, ge=0, le=86_400)
    projections: list[WorldProjectionDescriptor] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: ResourceType | str) -> ResourceType | str:
        _validate_resource_type_id(value)
        return value

    @model_validator(mode="after")
    def _validate_projections(self) -> "ResourceTypeDescriptor":
        ids = [item.id for item in self.projections]
        if len(ids) != len(set(ids)):
            raise ValueError("resource projections must not repeat IDs")
        return self


class WorldProviderDescriptor(BaseModel):
    """Static contract projected into the host-owned agent world graph."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=2_000)
    connection_id: str | None = Field(
        default=None, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$"
    )
    health_capability: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9_.-]{0,127}$"
    )
    resource_types: list[ResourceTypeDescriptor] = Field(default_factory=list, min_length=1)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_resources(self) -> "WorldProviderDescriptor":
        ids = [item.id.value if isinstance(item.id, ResourceType) else str(item.id) for item in self.resource_types]
        if len(ids) != len(set(ids)):
            raise ValueError("world provider resource types must not repeat IDs")
        return self


class CapabilityDescriptor(BaseModel):
    """Declarative capability contract shared by SDK, host, and plugins."""

    id: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=2_000)
    effect: CapabilityEffect
    tool: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    connection_id: str | None = Field(
        default=None, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$"
    )
    consumes: list[ResourceBinding] = Field(default_factory=list)
    produces: list[CapabilityOutputBinding] = Field(default_factory=list)
    inputs: list[CapabilityInputBinding] = Field(default_factory=list)
    requirements: CapabilityRequirement
    exposure: CapabilityExposure
    non_callable_reason: NonCallableReason | None = None
    prepared_action: PreparedActionDescriptor | None = None
    idempotency: IdempotencyDescriptor | None = None
    completion: CompletionDescriptor | None = None
    reviewable_action_id: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9-]{0,63}$"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_contract(self) -> "CapabilityDescriptor":
        if self.exposure == CapabilityExposure.MODEL and self.non_callable_reason is not None:
            raise ValueError("model exposure must not declare non_callable_reason")
        if self.exposure != CapabilityExposure.MODEL and self.non_callable_reason is None:
            raise ValueError("host/admin exposure requires non_callable_reason")
        if (
            self.reviewable_action_id
            and self.effect == CapabilityEffect.EXTERNAL_WRITE
            and self.exposure == CapabilityExposure.MODEL
        ):
            raise ValueError("reviewable delivery capabilities must be host-only")
        input_names = [item.semantic_field for item in self.inputs]
        if len(input_names) != len(set(input_names)):
            raise ValueError("capability inputs must not repeat semantic fields")
        output_names = [item.output_name for item in self.produces]
        if len(output_names) != len(set(output_names)):
            raise ValueError("capability outputs must not repeat output names")
        task_owned_types = {
            ResourceType.TASK.value,
            ResourceType.ARTIFACT.value,
            ResourceType.PREPARED_ACTION.value,
        }
        bound_types = {
            item.resource_type.value
            if isinstance(item.resource_type, ResourceType)
            else str(item.resource_type)
            for item in (*self.consumes, *self.produces)
        }
        if bound_types & task_owned_types and self.requirements.task_context != "required":
            raise ValueError("task-owned resources require task_context=required")
        if self.effect == CapabilityEffect.EXTERNAL_WRITE and self.exposure == CapabilityExposure.MODEL:
            missing = [
                name
                for name, value in (
                    ("prepared_action", self.prepared_action),
                    ("idempotency", self.idempotency),
                    ("completion", self.completion),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "model-selectable external writes require " + ", ".join(missing)
                )
            assert self.idempotency is not None
            if not self.idempotency.required_for_execution:
                raise ValueError(
                    "model-selectable external writes require execution idempotency"
                )
        if self.exposure == CapabilityExposure.MODEL and self.effect == CapabilityEffect.READ:
            if not self.produces:
                raise ValueError("model-selectable reads require declared outputs")
        if self.exposure == CapabilityExposure.MODEL and self.effect in {
            CapabilityEffect.WRITE,
            CapabilityEffect.EXTERNAL_WRITE,
        }:
            if not self.inputs:
                raise ValueError("model-selectable writes require declared inputs")
        return self


def normalize_capability_map(value: Any) -> list[CapabilityDescriptor]:
    """Parse a manifest capability list with a useful validation error."""
    if not isinstance(value, list):
        raise ValueError("capabilities must be a list of capability descriptors")
    return [CapabilityDescriptor.model_validate(item) for item in value]

"""Typed resource and capability contracts for Nutria plugin manifests."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


_RESOURCE_TYPE_PATTERN = r"^[a-z][a-z0-9_.-]{0,127}$"


class CapabilityEffect(str, Enum):
    READ = "read"
    PREPARE = "prepare"
    WRITE = "write"
    EXTERNAL_WRITE = "external_write"


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

    authority: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    connection_id: str | None = Field(default=None, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    audience: list[str] = Field(default_factory=list)

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
    """Maps a semantic input to one plugin tool argument."""

    semantic_field: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]{0,127}$")
    argument_name: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,127}$")
    resource_type: ResourceType | str | None = None
    required: bool = True

    model_config = {"extra": "forbid"}

    @field_validator("resource_type")
    @classmethod
    def _validate_resource_type(cls, value: ResourceType | str | None) -> ResourceType | str | None:
        if value is not None:
            _validate_resource_type_id(value)
        return value


class CapabilityOutputBinding(BaseModel):
    """Maps one plugin result field to a typed resource output."""

    field_name: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]{0,127}$")
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
    requirements: CapabilityRequirement = Field(default_factory=CapabilityRequirement)
    model_callable: bool = True
    reviewable_action_id: str | None = Field(
        default=None, pattern=r"^[a-z][a-z0-9-]{0,63}$"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_contract(self) -> "CapabilityDescriptor":
        if self.connection_id and self.requirements.connection_id not in (None, self.connection_id):
            raise ValueError("capability connection_id conflicts with its requirement")
        if (
            self.reviewable_action_id
            and self.effect == CapabilityEffect.EXTERNAL_WRITE
            and self.model_callable
        ):
            raise ValueError("reviewable delivery capabilities must be host-only")
        input_names = [item.semantic_field for item in self.inputs]
        if len(input_names) != len(set(input_names)):
            raise ValueError("capability inputs must not repeat semantic fields")
        output_names = [item.output_name for item in self.produces]
        if len(output_names) != len(set(output_names)):
            raise ValueError("capability outputs must not repeat output names")
        return self


def normalize_capability_map(value: Any) -> list[CapabilityDescriptor]:
    """Parse a manifest capability list with a useful validation error."""
    if not isinstance(value, list):
        raise ValueError("capabilities must be a list of capability descriptors")
    return [CapabilityDescriptor.model_validate(item) for item in value]

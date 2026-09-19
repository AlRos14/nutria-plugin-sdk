"""Stable capability-domain vocabulary shared by plugin manifests and hosts."""

from __future__ import annotations

from enum import Enum


class CapabilityDomain(str, Enum):
    """Business context domains used for progressive context disclosure."""

    PRODUCTS = "products"
    ORDERS = "orders"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    MRW = "mrw"
    TRELLO = "trello"
    TASKS = "tasks"


DOMAIN_LABELS: dict[CapabilityDomain, str] = {
    CapabilityDomain.PRODUCTS: "Productos",
    CapabilityDomain.ORDERS: "Pedidos",
    CapabilityDomain.WHATSAPP: "WhatsApp",
    CapabilityDomain.EMAIL: "Email",
    CapabilityDomain.MRW: "MRW",
    CapabilityDomain.TRELLO: "Trello",
    CapabilityDomain.TASKS: "Tareas",
}

CAPABILITY_DOMAIN_IDS = frozenset(domain.value for domain in CapabilityDomain)


def normalize_domains(values: list[str | CapabilityDomain]) -> tuple[str, ...]:
    """Return a stable, duplicate-free tuple of valid domain IDs."""

    normalized = tuple(
        dict.fromkeys(
            value.value if isinstance(value, CapabilityDomain) else str(value).strip()
            for value in values
        )
    )
    if not normalized or any(value not in CAPABILITY_DOMAIN_IDS for value in normalized):
        raise ValueError("capabilities must declare one or more known domains")
    return normalized

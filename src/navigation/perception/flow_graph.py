"""Phase 3: flow graph — verified checkpoints, not just routes."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .verification import SuccessCriteria


@dataclass(slots=True)
class Checkpoint:
    name: str
    success: SuccessCriteria
    instruction: str | None = None
    navigate_url: str | None = None
    ensure_url: str | None = None
    prerequisite_state: str | None = None
    max_steps: int = 8
    max_attempts: int = 3

    @property
    def is_deterministic(self) -> bool:
        return self.instruction is None and self.navigate_url is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": "deterministic" if self.is_deterministic else "agent",
            "navigate_url": self.navigate_url,
            "instruction": self.instruction,
            "ensure_url": self.ensure_url,
            "prerequisite_state": self.prerequisite_state,
            "success": {
                "url_contains": self.success.url_contains,
                "text_contains": self.success.text_contains,
            },
        }


@dataclass(slots=True)
class FlowGraph:
    name: str
    description: str
    checkpoints: list[Checkpoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "checkpoints": [c.to_dict() for c in self.checkpoints],
        }


def validation_form_flow() -> FlowGraph:
    return FlowGraph(
        name="validation-form",
        description="Probe validation rules then submit valid data",
        checkpoints=[
            Checkpoint(
                name="open-form",
                navigate_url="/forms/validation",
                success=SuccessCriteria(
                    url_contains=["/forms/validation"],
                    text_contains=["Validated form"],
                ),
            ),
            Checkpoint(
                name="submit-empty",
                instruction="Click Validate & submit without filling fields",
                ensure_url="/forms/validation",
                success=SuccessCriteria(
                    url_contains=["/forms/validation"],
                    text_contains=["Invalid email address"],
                ),
                max_steps=4,
            ),
            Checkpoint(
                name="submit-valid",
                instruction=(
                    "Fill Email test@example.com, Phone 1234567890, Age 25, "
                    "check terms, click Validate & submit"
                ),
                ensure_url="/forms/validation",
                success=SuccessCriteria(
                    url_contains=["/forms/validation"],
                    text_contains=["Form is valid"],
                ),
                max_steps=8,
            ),
        ],
    )


def shop_order_flow() -> FlowGraph:
    return FlowGraph(
        name="shop-order",
        description="Buy Pulse Watch through checkout",
        checkpoints=[
            Checkpoint(
                name="open-product",
                navigate_url="/shop/product/p3",
                success=SuccessCriteria(url_contains=["/shop/product/p3"]),
            ),
            Checkpoint(
                name="checkout-to-confirmation",
                instruction=(
                    "Buy now, checkout, fill shipping and payment, place order"
                ),
                prerequisite_state="cart_with_items",
                success=SuccessCriteria(url_contains=["/shop/checkout/confirmation"]),
                max_steps=35,
            ),
        ],
    )


FLOWS: dict[str, Callable[[], FlowGraph]] = {
    "validation-form": validation_form_flow,
    "shop-order": shop_order_flow,
}

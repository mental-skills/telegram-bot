from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RouteMode = Literal["full", "standalone"]


class ModuleIdentityError(ValueError):
    """Raised when a storage module ID is not valid for the current module."""


@dataclass(frozen=True)
class ModuleIdentity:
    """Public module identity with legacy storage compatibility.

    Storage IDs remain unchanged until an explicit data migration is approved.
    ``route_mode`` is an execution mode of the same module, not another module.
    """

    canonical_module_id: str
    full_route_storage_id: str
    standalone_storage_id: str
    registry_module_id: str

    def public_module_id(self, storage_id: str) -> str:
        if storage_id in {
            self.full_route_storage_id,
            self.standalone_storage_id,
        }:
            return self.canonical_module_id
        raise ModuleIdentityError(f"Unknown storage module ID: {storage_id}")

    def route_mode(self, storage_id: str) -> RouteMode:
        if storage_id == self.full_route_storage_id:
            return "full"
        if storage_id == self.standalone_storage_id:
            return "standalone"
        raise ModuleIdentityError(f"Unknown storage module ID: {storage_id}")

    def validate_registry(self, registry_module_id: str) -> None:
        if registry_module_id != self.registry_module_id:
            raise ModuleIdentityError(
                "Scenario registry is not bound to the current module: "
                f"{registry_module_id} != {self.registry_module_id}"
            )


CURRENT_MODULE = ModuleIdentity(
    canonical_module_id="parents_football_competition",
    full_route_storage_id="football_parent_mvp",
    standalone_storage_id="football_parent_standalone",
    registry_module_id="football_parent_mvp",
)

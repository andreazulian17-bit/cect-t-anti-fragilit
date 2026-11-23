
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
from .types import AttributeVector, SubstrateState, DomainInvariant, DomainModel


def make_temperature_domain() -> DomainModel:
    def lawful_range(**kwargs) -> float:
        realized = kwargs["realized"].as_map()["temperature"]
        lo, hi = 0.0, 1.5
        if realized < lo:
            return lo - realized
        if realized > hi:
            return realized - hi
        return 0.0

    invariants = (
        DomainInvariant("temperature_range", "bound", 1.0, lawful_range),
    )
    return DomainModel(
        invariants=invariants,
        target_bounds={"temperature": (0.0, 1.5)},
        transition_caps={"temperature": 0.45},
        min_energy_per_delta={"temperature": 0.22},
        directional_families={
            "warm": "increase",
            "stabilize": "hold",
            "cool": "decrease",
            "unsafe": "increase",
        },
    )


def substrate(value: float, instance_id: str, family: str = "temperature") -> SubstrateState:
    return SubstrateState(
        vector=AttributeVector(names=("temperature",), values=np.array([float(value)], dtype=float)),
        family=family,
        instance_id=instance_id,
    )


def substrate_bin(x: float) -> str:
    if x < 0.45:
        return "cold"
    if x < 0.75:
        return "warm_ready"
    return "hot"

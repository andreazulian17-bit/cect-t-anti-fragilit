
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
import numpy as np

Admissibility = Literal["possible", "contingent", "impossible_by_law", "degraded_constructor"]


@dataclass(frozen=True)
class AttributeVector:
    names: Tuple[str, ...]
    values: np.ndarray

    def copy(self) -> "AttributeVector":
        return AttributeVector(self.names, self.values.copy())

    def as_map(self) -> Dict[str, float]:
        return {n: float(v) for n, v in zip(self.names, self.values)}


@dataclass(frozen=True)
class SubstrateState:
    vector: AttributeVector
    family: str
    instance_id: str

    def copy(self) -> "SubstrateState":
        return SubstrateState(self.vector.copy(), self.family, self.instance_id)

    def as_map(self) -> Dict[str, float]:
        return self.vector.as_map()


@dataclass(frozen=True)
class DomainInvariant:
    name: str
    kind: str
    weight: float
    fn: Any


@dataclass(frozen=True)
class DomainModel:
    invariants: Tuple[DomainInvariant, ...]
    target_bounds: Dict[str, Tuple[float, float]]
    transition_caps: Dict[str, float]
    min_energy_per_delta: Dict[str, float]
    directional_families: Dict[str, str]


@dataclass(frozen=True)
class ContractSpec:
    label: str
    attribute_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    resource_mins: Dict[str, float] = field(default_factory=dict)
    integrity_min: float = 0.0
    require_lawful: bool = True


@dataclass(frozen=True)
class CapabilityRequirement:
    label: str
    min_confidence: float = 0.60
    min_diversity: int = 2


@dataclass(frozen=True)
class WarrantyRequirement:
    label: str
    min_confidence: float = 0.65
    min_robustness: float = 0.65
    min_integrity_reserve: float = 0.45
    min_energy_reserve: float = 0.18


@dataclass
class CapabilityCertificate:
    label: str
    task_family: str
    produced_contracts: Tuple[str, ...]
    confidence: float
    diversity_count: int
    support_count: int
    lawful_success_rate: float
    status: Literal["active", "stale", "revoked"] = "active"


@dataclass
class WarrantyCertificate:
    label: str
    capability_label: str
    task_family: str
    confidence: float
    robustness: float
    integrity_reserve: float
    energy_reserve: float
    support_count: int
    status: Literal["active", "stale", "revoked"] = "active"


@dataclass
class SharedKPMemory:
    family_credit: Dict[str, float] = field(default_factory=dict)
    contract_credit: Dict[str, float] = field(default_factory=dict)
    warranty_credit: Dict[str, float] = field(default_factory=dict)

    def positive(self, family: str, contracts: Sequence[str], credit: float) -> None:
        if credit <= 0:
            return
        self.family_credit[family] = self.family_credit.get(family, 0.0) + credit
        for c in contracts:
            self.contract_credit[c] = self.contract_credit.get(c, 0.0) + 0.8 * credit

    def warranty_boost(self, label: str, credit: float) -> None:
        self.warranty_credit[label] = self.warranty_credit.get(label, 0.0) + credit

    def penalize(self, family: str, contracts: Sequence[str], penalty: float) -> None:
        if penalty <= 0:
            return
        self.family_credit[family] = self.family_credit.get(family, 0.0) - penalty
        for c in contracts:
            self.contract_credit[c] = self.contract_credit.get(c, 0.0) - 0.4 * penalty

    def decay(self, factor: float = 0.985) -> None:
        for mapping in (self.family_credit, self.contract_credit, self.warranty_credit):
            for k in list(mapping.keys()):
                mapping[k] *= factor
                if abs(mapping[k]) < 1e-9:
                    del mapping[k]


@dataclass
class Recipe:
    name: str
    gain: float
    cost_factor: float
    task_families: Tuple[str, ...]
    support_postconditions: Tuple[str, ...] = ()
    exploit_preconditions: Tuple[str, ...] = ()
    compatible_warranties: Tuple[str, ...] = ()
    status: Literal["active", "quarantined", "retired"] = "active"
    success_count: int = 0
    failure_count: int = 0
    criticism_score: float = 0.0


@dataclass(frozen=True)
class TaskTransform:
    name: str
    family: str
    input_pattern: AttributeVector
    target_pattern: AttributeVector
    tolerance: float
    preconditions: Tuple[ContractSpec, ...] = ()
    postconditions: Tuple[ContractSpec, ...] = ()
    required_capabilities: Tuple[CapabilityRequirement, ...] = ()
    required_warranties: Tuple[WarrantyRequirement, ...] = ()
    resource_budget: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AtomicPlan:
    task: TaskTransform


@dataclass(frozen=True)
class SeqPlan:
    name: str
    steps: Tuple["PlanNode", ...]


@dataclass(frozen=True)
class ChoicePlan:
    name: str
    options: Tuple["PlanNode", ...]


@dataclass(frozen=True)
class RepeatPlan:
    name: str
    body: "PlanNode"
    max_repeats: int
    stop_tolerance: float
    stable_successes_required: int = 2
    kp_erosion_patience: int = 2
    min_integrity: float = 0.40
    min_energy: float = 0.10
    global_trend_window: int = 4
    min_recent_kp_trend: float = -0.02


@dataclass(frozen=True)
class CertifyPlan:
    name: str
    body: AtomicPlan
    probe_substrates: Tuple[SubstrateState, ...]
    certificate_label: str
    min_support: int = 3
    min_diversity: int = 2
    min_confidence: float = 0.60


@dataclass(frozen=True)
class WarrantyPlan:
    name: str
    body: AtomicPlan
    probe_substrates: Tuple[SubstrateState, ...]
    perturbations: Tuple[float, ...]
    capability_label: str
    warranty_label: str
    min_support: int = 5
    min_robustness: float = 0.65
    min_confidence: float = 0.65


PlanNode = Union[AtomicPlan, SeqPlan, ChoicePlan, RepeatPlan, CertifyPlan, WarrantyPlan]


@dataclass(frozen=True)
class EngineConfig:
    seed: int = 410
    integrity_min: float = 0.36
    kp_gain: float = 2.2
    kp_decay: float = 0.06
    lawful_bonus: float = 0.10
    impossible_penalty: float = 0.25
    contingent_penalty: float = 0.05
    postcondition_penalty: float = 0.08
    capability_penalty: float = 0.08
    warranty_penalty: float = 0.08
    resource_floor: float = 0.05
    sequence_handoff_min: float = 0.78
    minimum_total_kp_delta: float = 0.02
    global_viability_min: float = 0.55
    capability_diversity_weight: float = 0.20
    warranty_robustness_weight: float = 0.25


@dataclass
class ConstructorState:
    integrity: float
    kp: float
    control_bias: float
    resources: Dict[str, float]
    held_contracts: Dict[str, int] = field(default_factory=dict)
    memory: SharedKPMemory = field(default_factory=SharedKPMemory)
    capabilities: Dict[str, CapabilityCertificate] = field(default_factory=dict)
    warranties: Dict[str, WarrantyCertificate] = field(default_factory=dict)
    kp_trace: List[float] = field(default_factory=list)


@dataclass
class StepOutcome:
    success: bool
    admissibility: Admissibility
    substrate: SubstrateState
    delta: float
    kp_delta: float
    handoff: float
    chosen_recipe: str
    reasons: Tuple[str, ...] = ()
    note: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StructuralAssessment:
    status: Admissibility
    reasons: Tuple[str, ...]
    score: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CounterfactualCase:
    name: str
    substrate: SubstrateState
    note: str = ""


@dataclass(frozen=True)
class FamilyImpossibilityRequirement:
    min_cases: int = 3
    min_distinct_instances: int = 3
    min_confidence: float = 0.70
    require_shared_reason_class: bool = True


@dataclass
class FamilyImpossibilityCertificate:
    plan_name: str
    status: str
    confidence: float
    shared_reason_classes: Tuple[str, ...]
    witnessed_cases: Tuple[str, ...]
    mean_structural_score: float
    per_case: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    note: str = ""

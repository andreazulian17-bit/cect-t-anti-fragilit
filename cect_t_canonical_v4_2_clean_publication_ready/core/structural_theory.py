
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple
import numpy as np

from .types import *
from .engine import execute_plan, structural_admissibility, make_state, default_recipes


@dataclass(frozen=True)
class StructuralTheory:
    model: DomainModel
    requirement: FamilyImpossibilityRequirement = FamilyImpossibilityRequirement()


def _normalize_reason(reason: str) -> str:
    if 'claimed_postcondition' in reason or 'relational' in reason:
        return 'relational'
    if 'contract' in reason or 'choice' in reason or 'missing_precondition' in reason:
        return 'compositional'
    if 'constructor_' in reason or 'repeat_' in reason:
        return 'constructor_limit'
    if any(k in reason for k in ('target_out_of_bounds', 'delta_cap', 'directionality', 'energy_gap')):
        return 'domain_law'
    if 'warranty' in reason or 'capability' in reason:
        return 'constructor_limit'
    return 'structural_other'


def assess_plan(plan: PlanNode, substrate: SubstrateState, state: ConstructorState, model: DomainModel, cfg: EngineConfig) -> StructuralAssessment:
    task = None
    if isinstance(plan, AtomicPlan):
        task = plan.task
    if task is not None:
        return structural_admissibility(task, substrate, state, model)
    # symbolic family-level assessment by execution on a ghost state
    ghost = ConstructorState(state.integrity, state.kp, state.control_bias, dict(state.resources), dict(state.held_contracts), state.memory, dict(state.capabilities), dict(state.warranties), list(state.kp_trace))
    out = execute_plan(plan, substrate, ghost, default_recipes(), model, cfg, np.random.default_rng(cfg.seed))
    if out.success:
        return StructuralAssessment('possible', (), 0.0, {'via_execution': True})
    if out.admissibility == 'possible':
        return StructuralAssessment('contingent', tuple(out.reasons or ('execution_failed',)), 0.4)
    return StructuralAssessment(out.admissibility, tuple(out.reasons), 0.8, {'via_execution': True})


def certify_family_impossibility(plan: PlanNode, cases: Sequence[CounterfactualCase], theory: StructuralTheory, cfg: EngineConfig) -> FamilyImpossibilityCertificate:
    if len(cases) < theory.requirement.min_cases:
        return FamilyImpossibilityCertificate(getattr(plan, 'name', getattr(getattr(plan, 'task', None), 'name', 'plan')), 'insufficient_evidence', 0.0, (), tuple(c.name for c in cases), 0.0, note='too few counterfactual cases')
    results = []
    for case in cases:
        state = make_state()
        ass = assess_plan(plan, case.substrate, state, theory.model, cfg)
        results.append({
            'case': case.name,
            'status': ass.status,
            'reasons': list(ass.reasons),
            'reason_classes': sorted({_normalize_reason(r) for r in ass.reasons}),
            'score': float(ass.score),
            'note': case.note,
        })
    impossible = [r for r in results if r['status'] == 'impossible_by_law']
    distinct_instances = len({c.substrate.instance_id for c in cases})
    mean_score = float(np.mean([r['score'] for r in impossible])) if impossible else 0.0
    if impossible:
        shared = set(impossible[0]['reason_classes'])
        for r in impossible[1:]:
            shared &= set(r['reason_classes'])
    else:
        shared = set()
    impossible_ratio = len(impossible) / len(results)
    class_support = sum(bool(r['reason_classes']) for r in impossible) / len(results) if results else 0.0
    consistency_bonus = 0.15 if shared else 0.0
    diversity_bonus = min(0.15, 0.05 * max(0, distinct_instances - theory.requirement.min_distinct_instances + 1))
    confidence = min(1.0, 0.55 * impossible_ratio + 0.15 * min(1.0, mean_score) + 0.15 * class_support + consistency_bonus + diversity_bonus)
    all_impossible = len(impossible) == len(results)
    enough_diversity = distinct_instances >= theory.requirement.min_distinct_instances
    shared_ok = (not theory.requirement.require_shared_reason_class) or bool(shared)
    status = 'certified_impossible' if (all_impossible and enough_diversity and shared_ok and confidence >= theory.requirement.min_confidence) else 'not_certified'
    notes = []
    if not all_impossible:
        notes.append('not impossible in all witnessed cases')
    if not enough_diversity:
        notes.append('insufficient substrate diversity')
    if theory.requirement.require_shared_reason_class and not shared:
        notes.append('no stable structural reason class across cases')
    if confidence < theory.requirement.min_confidence:
        notes.append('confidence below threshold')
    if not notes:
        notes.append('counterfactual family impossibility certified')
    return FamilyImpossibilityCertificate(
        plan_name=getattr(plan, 'name', getattr(getattr(plan, 'task', None), 'name', 'plan')),
        status=status,
        confidence=float(confidence),
        shared_reason_classes=tuple(sorted(shared)),
        witnessed_cases=tuple(c.name for c in cases),
        mean_structural_score=float(mean_score),
        per_case=tuple(results),
        note='; '.join(notes),
    )

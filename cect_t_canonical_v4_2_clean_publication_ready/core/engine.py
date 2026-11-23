
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math
import numpy as np

from .types import *
from .domain import substrate, substrate_bin


def default_contracts() -> Dict[str, ContractSpec]:
    return {
        "warm_ready": ContractSpec("warm_ready", {"temperature": (0.45, 0.80)}, {"energy": 0.05}, 0.35),
        "stable": ContractSpec("stable", {"temperature": (0.58, 0.72)}, {"energy": 0.05}, 0.35),
        "cool_ready": ContractSpec("cool_ready", {"temperature": (0.20, 0.50)}, {"energy": 0.05}, 0.35),
    }


def default_recipes() -> List[Recipe]:
    return [
        Recipe("warm_specialist", 0.34, 0.24, ("warm",), support_postconditions=("warm_ready",)),
        Recipe("stabilize_contractual", 0.24, 0.18, ("stabilize",), exploit_preconditions=("warm_ready",), support_postconditions=("stable",), compatible_warranties=("safe_warranty",)),
        Recipe("safe_path", 0.22, 0.15, ("stabilize", "cool"), exploit_preconditions=("warm_ready",), support_postconditions=("stable",), compatible_warranties=("safe_warranty",)),
        Recipe("unsafe_claim", 0.44, 0.34, ("unsafe",), support_postconditions=("stable",)),
        Recipe("cooling", 0.28, 0.16, ("cool",), support_postconditions=("cool_ready",)),
    ]


def make_state() -> ConstructorState:
    return ConstructorState(integrity=1.0, kp=0.0, control_bias=0.0, resources={"energy": 1.0})


def make_tasks(contracts: Dict[str, ContractSpec]) -> Dict[str, TaskTransform]:
    def av(x: float) -> AttributeVector:
        return AttributeVector(("temperature",), np.array([x], dtype=float))

    return {
        "warm": TaskTransform("warm", "warm", av(0.20), av(0.60), 0.06, postconditions=(contracts["warm_ready"],), resource_budget={"energy": 0.16}),
        "stabilize": TaskTransform("stabilize", "stabilize", av(0.60), av(0.65), 0.05, preconditions=(contracts["warm_ready"],), postconditions=(contracts["stable"],), resource_budget={"energy": 0.12}),
        "cool": TaskTransform("cool", "cool", av(0.80), av(0.40), 0.06, postconditions=(contracts["cool_ready"],), resource_budget={"energy": 0.12}),
        "unsafe_claim_stable": TaskTransform("unsafe_claim_stable", "unsafe", av(0.55), av(1.15), 0.07, postconditions=(contracts["stable"],), resource_budget={"energy": 0.20}),
        "hold_hot": TaskTransform("hold_hot", "unsafe", av(1.00), av(1.15), 0.05, postconditions=(contracts["stable"],), resource_budget={"energy": 0.18}),
    }


def available_contract_labels(state: ConstructorState) -> Tuple[str, ...]:
    return tuple(sorted(k for k, ttl in state.held_contracts.items() if ttl > 0))


def _substrate_meets_contract(contract: ContractSpec, substrate: SubstrateState, state: ConstructorState) -> bool:
    s_map = substrate.as_map()
    for name, (lo, hi) in contract.attribute_ranges.items():
        if name not in s_map or not (lo <= s_map[name] <= hi):
            return False
    if state.integrity < contract.integrity_min:
        return False
    for r, minimum in contract.resource_mins.items():
        if float(state.resources.get(r, 0.0)) < minimum:
            return False
    return True


def contract_satisfied(contract: ContractSpec, substrate: SubstrateState, state: ConstructorState, lawful: bool) -> bool:
    s_map = substrate.as_map()
    for name, (lo, hi) in contract.attribute_ranges.items():
        if name not in s_map or not (lo <= s_map[name] <= hi):
            return False
    for r, minimum in contract.resource_mins.items():
        if float(state.resources.get(r, 0.0)) < minimum:
            return False
    if state.integrity < contract.integrity_min:
        return False
    if contract.require_lawful and not lawful:
        return False
    return True


def decay_contract_inventory(state: ConstructorState) -> None:
    for k in list(state.held_contracts.keys()):
        state.held_contracts[k] -= 1
        if state.held_contracts[k] <= 0:
            del state.held_contracts[k]


def recent_kp_trend(state: ConstructorState, window: int) -> float:
    if len(state.kp_trace) < 2:
        return 0.0
    hist = state.kp_trace[-window:]
    if len(hist) < 2:
        return 0.0
    return float((hist[-1] - hist[0]) / max(1, len(hist) - 1))


def global_viability(state: ConstructorState, cfg: EngineConfig) -> float:
    energy = float(state.resources.get("energy", 0.0))
    return float(np.clip(0.45 * state.integrity + 0.25 * max(0.0, min(1.0, energy)) + 0.30 * max(0.0, min(1.0, 0.5 + state.kp)), 0.0, 1.0))


def handoff_score(substrate_a: SubstrateState, task_b: TaskTransform) -> float:
    target = task_b.input_pattern.as_map()
    actual = substrate_a.as_map()
    errs = []
    for k, v in target.items():
        errs.append(abs(actual.get(k, 0.0) - v))
    if not errs:
        return 1.0
    mean_err = float(np.mean(errs))
    return float(max(0.0, 1.0 - mean_err / 0.50))


def structural_admissibility(task: TaskTransform, substrate: SubstrateState, state: ConstructorState, model: DomainModel) -> StructuralAssessment:
    reasons: List[str] = []
    score = 0.0
    if state.integrity < 0.36:
        return StructuralAssessment("degraded_constructor", ("constructor_integrity_below_min",), 1.0)

    for pre in task.preconditions:
        if pre.label not in available_contract_labels(state) and not _substrate_meets_contract(pre, substrate, state):
            reasons.append(f"missing_precondition:{pre.label}")

    for cap in task.required_capabilities:
        cert = state.capabilities.get(cap.label)
        if cert is None or cert.status != "active" or cert.confidence < cap.min_confidence or cert.diversity_count < cap.min_diversity:
            reasons.append(f"capability_missing:{cap.label}")

    for req in task.required_warranties:
        war = state.warranties.get(req.label)
        if war is None or war.status != "active" or war.confidence < req.min_confidence or war.robustness < req.min_robustness:
            reasons.append(f"warranty_missing:{req.label}")

    current = substrate.as_map()["temperature"]
    target = task.target_pattern.as_map()["temperature"]
    delta = abs(target - current)
    energy_need = delta * model.min_energy_per_delta["temperature"]
    if float(state.resources.get("energy", 0.0)) < energy_need:
        reasons.append("energy_gap")

    lo, hi = model.target_bounds["temperature"]
    if not (lo <= target <= hi):
        reasons.append("target_out_of_bounds")

    if delta > model.transition_caps["temperature"]:
        reasons.append("delta_cap_exceeded")

    fam_dir = model.directional_families.get(task.family, "hold")
    if fam_dir == "increase" and target < current - 1e-9:
        reasons.append("directionality_violation")
    if fam_dir == "decrease" and target > current + 1e-9:
        reasons.append("directionality_violation")
    if task.family == "unsafe" and any(pc.label == "stable" for pc in task.postconditions) and target > 0.95:
        reasons.append("claimed_postcondition_relational_mismatch")

    if reasons:
        if any(r in reasons for r in ("target_out_of_bounds", "delta_cap_exceeded", "directionality_violation", "claimed_postcondition_relational_mismatch")):
            status = "impossible_by_law"
            score = min(1.0, 0.2 * len(reasons) + 0.2)
        else:
            status = "contingent"
            score = min(1.0, 0.1 * len(reasons) + 0.1)
        return StructuralAssessment(status, tuple(reasons), score)
    return StructuralAssessment("possible", (), 0.0)


def select_recipe(task: TaskTransform, substrate: SubstrateState, state: ConstructorState, recipes: Sequence[Recipe]) -> Recipe:
    labels = available_contract_labels(state)
    best: Optional[Tuple[float, Recipe]] = None
    for recipe in recipes:
        if recipe.status != "active":
            continue
        family_bonus = 1.0 if task.family in recipe.task_families else 0.0
        pre_bonus = sum(0.25 for x in labels if x in recipe.exploit_preconditions)
        post_bonus = sum(0.25 for pc in task.postconditions if pc.label in recipe.support_postconditions)
        hist = 0.10 * recipe.success_count - 0.09 * recipe.failure_count - 0.07 * recipe.criticism_score
        mem = 0.12 * state.memory.family_credit.get(task.family, 0.0)
        mem += 0.08 * sum(state.memory.contract_credit.get(l, 0.0) for l in labels)
        warranty_bonus = 0.15 * sum(state.memory.warranty_credit.get(w.label, 0.0) for w in task.required_warranties if w.label in recipe.compatible_warranties)
        energy = float(state.resources.get("energy", 0.0))
        reserve_term = 0.04 * energy / (1.0 + recipe.cost_factor)
        score = family_bonus + pre_bonus + post_bonus + hist + mem + warranty_bonus + reserve_term + recipe.gain - 0.50 * recipe.cost_factor
        if best is None or score > best[0]:
            best = (score, recipe)
    assert best is not None
    return best[1]


def realize(task: TaskTransform, recipe: Recipe, substrate: SubstrateState, state: ConstructorState, rng: np.random.Generator) -> SubstrateState:
    current = substrate.as_map()["temperature"]
    target = task.target_pattern.as_map()["temperature"]
    direction = target - current
    family_match = 1.0 if task.family in recipe.task_families else 0.0
    alpha = min(0.98, 0.72 + 0.18 * family_match + 0.12 * recipe.gain + 0.04 * state.control_bias)
    noise = float(rng.normal(0.0, 0.004))
    new_value = current + alpha * direction + noise
    return substrate.__class__(
        vector=AttributeVector(("temperature",), np.array([new_value], dtype=float)),
        family=substrate.family,
        instance_id=substrate.instance_id,
    )


def compute_law_violation(realized: SubstrateState, substrate: SubstrateState, recipe: Recipe, model: DomainModel) -> float:
    total = 0.0
    for inv in model.invariants:
        total += inv.weight * max(0.0, float(inv.fn(realized=realized, substrate=substrate, recipe=recipe))) ** 2
    return float(total)


def compute_delta(realized: SubstrateState, task: TaskTransform) -> float:
    return abs(realized.as_map()["temperature"] - task.target_pattern.as_map()["temperature"])


def update_state_after_step(task: TaskTransform, realized: SubstrateState, recipe: Recipe, state: ConstructorState, lawful: bool, delta: float, law_v: float, cfg: EngineConfig) -> float:
    resource_cost = float(task.resource_budget.get("energy", 0.08)) * (1.0 + recipe.cost_factor)
    state.resources["energy"] = max(0.0, float(state.resources.get("energy", 0.0)) - resource_cost)
    if lawful:
        improvement = max(0.0, task.tolerance - delta + 0.10)
        kp_delta = cfg.kp_gain * improvement - cfg.kp_decay * law_v + cfg.lawful_bonus
        state.integrity = min(1.0, state.integrity - 0.015 * resource_cost + 0.02)
        state.memory.positive(task.family, [pc.label for pc in task.postconditions], max(0.0, kp_delta))
        recipe.success_count += 1
    else:
        kp_delta = -cfg.impossible_penalty if law_v > 0.0 else -cfg.contingent_penalty
        state.integrity = max(0.0, state.integrity - 0.03 - 0.03 * law_v)
        state.memory.penalize(task.family, [pc.label for pc in task.postconditions], abs(kp_delta))
        recipe.failure_count += 1
        recipe.criticism_score += 0.3 + law_v
    state.kp += kp_delta
    state.kp_trace.append(state.kp)
    return float(kp_delta)


def _apply_postconditions(task: TaskTransform, realized: SubstrateState, state: ConstructorState, lawful: bool) -> Tuple[str, ...]:
    satisfied = []
    for pc in task.postconditions:
        if contract_satisfied(pc, realized, state, lawful):
            state.held_contracts[pc.label] = max(state.held_contracts.get(pc.label, 0), 3)
            satisfied.append(pc.label)
    return tuple(satisfied)


def execute_atomic(plan: AtomicPlan, substrate: SubstrateState, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:
    decay_contract_inventory(state)
    task = plan.task
    assessment = structural_admissibility(task, substrate, state, model)
    if assessment.status != "possible":
        state.kp += -cfg.contingent_penalty if assessment.status == "contingent" else -cfg.impossible_penalty
        state.kp_trace.append(state.kp)
        return StepOutcome(False, assessment.status, substrate.copy(), math.inf, -cfg.contingent_penalty, 0.0, "none", assessment.reasons, details=assessment.details)

    recipe = select_recipe(task, substrate, state, recipes)
    realized = realize(task, recipe, substrate, state, rng)
    law_v = compute_law_violation(realized, substrate, recipe, model)
    delta = compute_delta(realized, task)
    lawful = law_v <= 1e-9 and delta <= max(task.tolerance * 1.25, 0.06)
    kp_delta = update_state_after_step(task, realized, recipe, state, lawful, delta, law_v, cfg)
    held = _apply_postconditions(task, realized, state, lawful)
    ok = lawful and delta <= task.tolerance and all(pc.label in held for pc in task.postconditions)
    return StepOutcome(ok, "possible" if lawful else "contingent", realized, float(delta), float(kp_delta), 1.0, recipe.name, details={"held": held, "law_violation": law_v})


def issue_certificate(plan: CertifyPlan, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:
    supports = 0
    lawful = 0
    diversity = set()
    for probe in plan.probe_substrates:
        local = ConstructorState(state.integrity, state.kp, state.control_bias, dict(state.resources), dict(state.held_contracts), state.memory, dict(state.capabilities), dict(state.warranties), list(state.kp_trace))
        out = execute_atomic(plan.body, probe, local, recipes, model, cfg, rng)
        if out.admissibility == "possible":
            lawful += 1
        if out.success:
            supports += 1
            diversity.add(substrate_bin(out.substrate.as_map()["temperature"]))
    confidence = lawful / max(1, len(plan.probe_substrates))
    cert = CapabilityCertificate(plan.certificate_label, plan.body.task.family, tuple(pc.label for pc in plan.body.task.postconditions), confidence, len(diversity), supports, confidence, status="active" if (supports >= plan.min_support and len(diversity) >= plan.min_diversity and confidence >= plan.min_confidence) else "stale")
    state.capabilities[plan.certificate_label] = cert
    return StepOutcome(cert.status == "active", "possible", plan.probe_substrates[-1].copy(), 0.0, 0.02 if cert.status == "active" else -0.02, 1.0, "certificate", details={"certificate": cert})


def perturb(sub: SubstrateState, eps: float) -> SubstrateState:
    x = sub.as_map()["temperature"]
    return substrate(x + eps, sub.instance_id + f"_p{eps:+.2f}", sub.family)


def issue_warranty(plan: WarrantyPlan, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:
    cap = state.capabilities.get(plan.capability_label)
    if cap is None or cap.status != "active":
        return StepOutcome(False, "contingent", plan.probe_substrates[-1].copy(), math.inf, -0.03, 0.0, "warranty", reasons=("capability_missing",))
    trials = 0
    successes = 0
    integ = []
    eners = []
    for probe in plan.probe_substrates:
        for eps in plan.perturbations:
            local = make_state()
            local.capabilities.update(state.capabilities)
            out = execute_atomic(plan.body, perturb(probe, eps), local, recipes, model, cfg, rng)
            trials += 1
            if out.success:
                successes += 1
            integ.append(local.integrity)
            eners.append(local.resources.get("energy", 0.0))
    robustness = successes / max(1, trials)
    confidence = min(1.0, 0.5 * cap.confidence + 0.5 * robustness)
    war = WarrantyCertificate(plan.warranty_label, plan.capability_label, plan.body.task.family, confidence, robustness, float(np.mean(integ) if integ else 0.0), float(np.mean(eners) if eners else 0.0), trials, status="active" if (trials >= plan.min_support and robustness >= plan.min_robustness and confidence >= plan.min_confidence) else "stale")
    state.warranties[plan.warranty_label] = war
    if war.status == "active":
        state.memory.warranty_boost(war.label, 0.25)
    return StepOutcome(war.status == "active", "possible", plan.probe_substrates[-1].copy(), 0.0, 0.03 if war.status == "active" else -0.02, 1.0, "warranty", details={"warranty": war})


def execute_plan(plan: PlanNode, substrate: SubstrateState, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:
    if isinstance(plan, AtomicPlan):
        return execute_atomic(plan, substrate, state, recipes, model, cfg, rng)
    if isinstance(plan, CertifyPlan):
        return issue_certificate(plan, state, recipes, model, cfg, rng)
    if isinstance(plan, WarrantyPlan):
        return issue_warranty(plan, state, recipes, model, cfg, rng)
    if isinstance(plan, SeqPlan):
        current = substrate
        total_kp = 0.0
        reasons: List[str] = []
        for i, step in enumerate(plan.steps):
            out = execute_plan(step, current, state, recipes, model, cfg, rng)
            total_kp += out.kp_delta
            reasons.extend(out.reasons)
            if not out.success:
                return StepOutcome(False, out.admissibility, out.substrate, out.delta, total_kp, 0.0, out.chosen_recipe, tuple(reasons), note=f"failed at step {i}")
            if i + 1 < len(plan.steps):
                next_task = _first_atomic_task(plan.steps[i+1])
                if next_task is not None:
                    h = handoff_score(out.substrate, next_task)
                    if h < cfg.sequence_handoff_min:
                        return StepOutcome(False, "impossible_by_law", out.substrate, out.delta, total_kp, h, out.chosen_recipe, tuple(reasons + ["contract_chain_unsatisfied"]), note="handoff below threshold")
            current = out.substrate
        return StepOutcome(total_kp >= cfg.minimum_total_kp_delta and global_viability(state, cfg) >= cfg.global_viability_min, "possible", current, 0.0, total_kp, 1.0, "sequence", tuple(reasons))
    if isinstance(plan, ChoicePlan):
        best: Optional[StepOutcome] = None
        best_score = -1e9
        best_reasons: Tuple[str, ...] = ()
        for opt in plan.options:
            ghost = ConstructorState(state.integrity, state.kp, state.control_bias, dict(state.resources), dict(state.held_contracts), state.memory, dict(state.capabilities), dict(state.warranties), list(state.kp_trace))
            out = execute_plan(opt, substrate.copy(), ghost, recipes, model, cfg, rng)
            score = (0.7 if out.success else -0.2) + out.kp_delta - 0.1 * max(0.0, out.delta if math.isfinite(out.delta) else 1.0)
            if out.admissibility == "impossible_by_law":
                score -= 0.6
            if score > best_score:
                best_score = score
                best = out
                best_reasons = out.reasons
        assert best is not None
        return execute_plan(plan.options[best_score == best_score and plan.options.index(next(o for o in plan.options if True)) if False else 0], substrate, state, recipes, model, cfg, rng)  # unreachable helper
    if isinstance(plan, RepeatPlan):
        current = substrate
        total_kp = 0.0
        stable = 0
        erosions = 0
        last_out = None
        for _ in range(plan.max_repeats):
            if state.integrity < plan.min_integrity or float(state.resources.get("energy", 0.0)) < plan.min_energy:
                return StepOutcome(False, "degraded_constructor", current, math.inf, total_kp, 0.0, "repeat", reasons=("repeat_constructor_limit",))
            out = execute_plan(plan.body, current, state, recipes, model, cfg, rng)
            total_kp += out.kp_delta
            if out.success and out.delta <= plan.stop_tolerance:
                stable += 1
            else:
                stable = 0
            if recent_kp_trend(state, plan.global_trend_window) < plan.min_recent_kp_trend:
                erosions += 1
            else:
                erosions = 0
            current = out.substrate
            last_out = out
            if stable >= plan.stable_successes_required:
                return StepOutcome(True, "possible", current, out.delta, total_kp, 1.0, out.chosen_recipe)
            if erosions >= plan.kp_erosion_patience:
                return StepOutcome(False, "contingent", current, out.delta, total_kp, 1.0, out.chosen_recipe, reasons=("global_kp_erosion",))
        if last_out is None:
            return StepOutcome(False, "contingent", current, math.inf, 0.0, 0.0, "repeat")
        return StepOutcome(False, "contingent", current, last_out.delta, total_kp, 1.0, last_out.chosen_recipe, reasons=("repeat_limit",))
    raise TypeError(f"unsupported plan type: {type(plan)!r}")


def _first_atomic_task(plan: PlanNode) -> Optional[TaskTransform]:
    if isinstance(plan, AtomicPlan):
        return plan.task
    if isinstance(plan, CertifyPlan):
        return plan.body.task
    if isinstance(plan, WarrantyPlan):
        return plan.body.task
    if isinstance(plan, SeqPlan) and plan.steps:
        return _first_atomic_task(plan.steps[0])
    if isinstance(plan, RepeatPlan):
        return _first_atomic_task(plan.body)
    return None


def _choice_execute(plan: ChoicePlan, substrate: SubstrateState, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:
    ranked = []
    for opt in plan.options:
        ghost = ConstructorState(state.integrity, state.kp, state.control_bias, dict(state.resources), dict(state.held_contracts), state.memory, dict(state.capabilities), dict(state.warranties), list(state.kp_trace))
        out = execute_plan(opt, substrate.copy(), ghost, recipes, model, cfg, rng)
        score = (0.7 if out.success else -0.2) + out.kp_delta - 0.1 * max(0.0, out.delta if math.isfinite(out.delta) else 1.0)
        if out.admissibility == "impossible_by_law":
            score -= 0.6
        ranked.append((score, opt))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return execute_plan(ranked[0][1], substrate, state, recipes, model, cfg, rng)

# patch choice dispatch cleanly
_old_execute_plan = execute_plan

def execute_plan(plan: PlanNode, substrate: SubstrateState, state: ConstructorState, recipes: Sequence[Recipe], model: DomainModel, cfg: EngineConfig, rng: np.random.Generator) -> StepOutcome:  # type: ignore[override]
    if isinstance(plan, ChoicePlan):
        return _choice_execute(plan, substrate, state, recipes, model, cfg, rng)
    return _old_execute_plan(plan, substrate, state, recipes, model, cfg, rng)

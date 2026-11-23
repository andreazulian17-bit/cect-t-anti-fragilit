from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple
import copy
import math
import numpy as np

from .types import ConstructorState, DomainModel, EngineConfig, PlanNode, SubstrateState
from .engine import execute_plan, global_viability


@dataclass(frozen=True)
class EnvironmentContext:
    name: str
    substrate_shift: float = 0.0
    bound_shift: float = 0.0
    transition_scale: float = 1.0
    energy_scale: float = 1.0
    resource_delta: float = 0.0
    integrity_drain: float = 0.0


@dataclass(frozen=True)
class EpisodeCase:
    name: str
    substrate: SubstrateState
    context: EnvironmentContext
    note: str = ""


@dataclass(frozen=True)
class PersistenceRequirement:
    min_episodes: int = 4
    min_context_diversity: int = 2
    min_success_rate: float = 0.75
    min_final_viability: float = 0.58
    min_mean_viability: float = 0.55
    max_integrity_drop: float = 0.42
    max_negative_kp_episodes: int = 1
    min_recent_kp_trend: float = -0.03


@dataclass
class PersistenceCertificate:
    label: str
    status: str
    confidence: float
    success_rate: float
    context_diversity: int
    final_viability: float
    mean_viability: float
    max_integrity_drop: float
    negative_kp_episodes: int
    kp_trend: float
    witnessed_episodes: Tuple[str, ...]
    per_episode: Tuple[Dict[str, object], ...] = field(default_factory=tuple)
    note: str = ""


def _clone_state(state: ConstructorState) -> ConstructorState:
    return ConstructorState(
        integrity=float(state.integrity),
        kp=float(state.kp),
        control_bias=float(state.control_bias),
        resources=dict(state.resources),
        held_contracts=dict(state.held_contracts),
        memory=copy.deepcopy(state.memory),
        capabilities=copy.deepcopy(state.capabilities),
        warranties=copy.deepcopy(state.warranties),
        kp_trace=list(state.kp_trace),
    )


def _clone_model(model: DomainModel, ctx: EnvironmentContext) -> DomainModel:
    target_bounds = {k: (lo + ctx.bound_shift, hi + ctx.bound_shift) for k, (lo, hi) in model.target_bounds.items()}
    transition_caps = {k: float(v) * ctx.transition_scale for k, v in model.transition_caps.items()}
    min_energy_per_delta = {k: float(v) * ctx.energy_scale for k, v in model.min_energy_per_delta.items()}
    return DomainModel(
        invariants=model.invariants,
        target_bounds=target_bounds,
        transition_caps=transition_caps,
        min_energy_per_delta=min_energy_per_delta,
        directional_families=dict(model.directional_families),
    )


def _shift_substrate(substrate: SubstrateState, shift: float, suffix: str) -> SubstrateState:
    vec = substrate.vector
    shifted = type(vec)(names=vec.names, values=vec.values.copy() + shift)
    return SubstrateState(vector=shifted, family=substrate.family, instance_id=f"{substrate.instance_id}_{suffix}")


def _apply_context_to_state(state: ConstructorState, ctx: EnvironmentContext, cfg: EngineConfig) -> None:
    state.integrity = float(np.clip(state.integrity - ctx.integrity_drain, 0.0, 1.0))
    state.resources["energy"] = float(np.clip(state.resources.get("energy", 0.0) + ctx.resource_delta, cfg.resource_floor, 1.0))


def _maintenance_step(state: ConstructorState) -> None:
    state.integrity = float(np.clip(state.integrity + 0.05, 0.0, 1.0))
    state.resources["energy"] = float(np.clip(state.resources.get("energy", 0.0) + 0.14, 0.0, 1.0))
    state.control_bias *= 0.92
    for label in list(state.held_contracts.keys()):
        state.held_contracts[label] -= 1
        if state.held_contracts[label] <= 0:
            del state.held_contracts[label]
    state.memory.decay(0.99)


def certify_constructor_persistence(
    label: str,
    plan: PlanNode,
    episodes: Sequence[EpisodeCase],
    base_state: ConstructorState,
    recipes,
    model: DomainModel,
    cfg: EngineConfig,
    seed: int | None = None,
    requirement: PersistenceRequirement | None = None,
) -> tuple[PersistenceCertificate, ConstructorState]:
    requirement = requirement or PersistenceRequirement()
    if len(episodes) < requirement.min_episodes:
        cert = PersistenceCertificate(
            label=label,
            status="not_certified",
            confidence=0.0,
            success_rate=0.0,
            context_diversity=len({e.context.name for e in episodes}),
            final_viability=0.0,
            mean_viability=0.0,
            max_integrity_drop=0.0,
            negative_kp_episodes=0,
            kp_trend=0.0,
            witnessed_episodes=tuple(e.name for e in episodes),
            note="too few episodes",
        )
        return cert, _clone_state(base_state)

    rng = np.random.default_rng(cfg.seed if seed is None else seed)
    state = _clone_state(base_state)
    start_integrity = state.integrity
    per_episode: List[Dict[str, object]] = []
    kp_deltas: List[float] = []
    viabilities: List[float] = []
    successes = 0
    negative_kp_episodes = 0

    for idx, episode in enumerate(episodes):
        _apply_context_to_state(state, episode.context, cfg)
        local_model = _clone_model(model, episode.context)
        local_substrate = _shift_substrate(episode.substrate, episode.context.substrate_shift, episode.context.name)
        out = execute_plan(plan, local_substrate, state, recipes, local_model, cfg, rng)
        viability = global_viability(state, cfg)
        successes += int(out.success)
        if out.kp_delta < 0:
            negative_kp_episodes += 1
        kp_deltas.append(float(out.kp_delta))
        viabilities.append(float(viability))
        per_episode.append(
            {
                "episode": episode.name,
                "context": episode.context.name,
                "success": bool(out.success),
                "admissibility": out.admissibility,
                "kp_delta": float(out.kp_delta),
                "viability": float(viability),
                "integrity": float(state.integrity),
                "energy": float(state.resources.get("energy", 0.0)),
                "reasons": list(out.reasons),
                "note": episode.note,
            }
        )
        if idx + 1 < len(episodes):
            _maintenance_step(state)

    success_rate = successes / len(episodes)
    context_diversity = len({e.context.name for e in episodes})
    final_viability = float(viabilities[-1]) if viabilities else 0.0
    mean_viability = float(np.mean(viabilities)) if viabilities else 0.0
    max_integrity_drop = float(max(0.0, start_integrity - min(ep["integrity"] for ep in per_episode))) if per_episode else 0.0
    if len(kp_deltas) >= 2:
        # simple least-squares slope over episodes
        x = np.arange(len(kp_deltas), dtype=float)
        kp_trend = float(np.polyfit(x, np.array(kp_deltas, dtype=float), 1)[0])
    else:
        kp_trend = float(kp_deltas[0]) if kp_deltas else 0.0

    confidence = min(
        1.0,
        0.30 * success_rate
        + 0.20 * min(1.0, mean_viability)
        + 0.20 * min(1.0, final_viability)
        + 0.15 * min(1.0, context_diversity / max(1, requirement.min_context_diversity))
        + 0.15 * max(0.0, 1.0 - max_integrity_drop),
    )

    certified = (
        success_rate >= requirement.min_success_rate
        and context_diversity >= requirement.min_context_diversity
        and final_viability >= requirement.min_final_viability
        and mean_viability >= requirement.min_mean_viability
        and max_integrity_drop <= requirement.max_integrity_drop
        and negative_kp_episodes <= requirement.max_negative_kp_episodes
        and kp_trend >= requirement.min_recent_kp_trend
    )

    notes: List[str] = []
    if success_rate < requirement.min_success_rate:
        notes.append("success rate below threshold")
    if context_diversity < requirement.min_context_diversity:
        notes.append("insufficient context diversity")
    if final_viability < requirement.min_final_viability:
        notes.append("final viability below threshold")
    if mean_viability < requirement.min_mean_viability:
        notes.append("mean viability below threshold")
    if max_integrity_drop > requirement.max_integrity_drop:
        notes.append("integrity drop too large")
    if negative_kp_episodes > requirement.max_negative_kp_episodes:
        notes.append("too many negative-KP episodes")
    if kp_trend < requirement.min_recent_kp_trend:
        notes.append("KP trend too negative")
    if certified:
        notes.append("constructor persistence certified")

    cert = PersistenceCertificate(
        label=label,
        status="certified_persistent" if certified else "not_certified",
        confidence=float(confidence),
        success_rate=float(success_rate),
        context_diversity=int(context_diversity),
        final_viability=float(final_viability),
        mean_viability=float(mean_viability),
        max_integrity_drop=float(max_integrity_drop),
        negative_kp_episodes=int(negative_kp_episodes),
        kp_trend=float(kp_trend),
        witnessed_episodes=tuple(e.name for e in episodes),
        per_episode=tuple(per_episode),
        note="; ".join(notes),
    )
    return cert, state

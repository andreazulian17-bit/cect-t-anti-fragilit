from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks, execute_plan
from cect_t_canonical_v4_2_clean_publication_ready.core.structural_theory import StructuralTheory, certify_family_impossibility
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import EnvironmentContext, EpisodeCase, PersistenceRequirement, certify_constructor_persistence
from cect_t_canonical_v4_2_clean_publication_ready.core.types import *


def run() -> dict:
    cfg = EngineConfig()
    model = make_temperature_domain()
    theory = StructuralTheory(model=model)
    contracts = default_contracts()
    tasks = make_tasks(contracts)
    recipes = default_recipes()
    seq = SeqPlan('warm_then_stabilize', (AtomicPlan(tasks['warm']), AtomicPlan(tasks['stabilize'])))

    results = {}

    cert1, final1 = certify_constructor_persistence(
        'mild_persistence',
        seq,
        [
            EpisodeCase('p1', substrate(0.20, 'p1'), EnvironmentContext('nominal')),
            EpisodeCase('p2', substrate(0.22, 'p2'), EnvironmentContext('mild_shift', substrate_shift=0.02, resource_delta=-0.04)),
            EpisodeCase('p3', substrate(0.18, 'p3'), EnvironmentContext('mild_drag', transition_scale=0.98, energy_scale=1.02, integrity_drain=0.01)),
            EpisodeCase('p4', substrate(0.21, 'p4'), EnvironmentContext('nominal_plus', substrate_shift=0.01, resource_delta=-0.02)),
        ],
        make_state(),
        recipes,
        model,
        cfg,
        seed=20,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    results['persistence_certified_mild'] = {
        'status': cert1.status,
        'confidence': cert1.confidence,
        'success_rate': cert1.success_rate,
        'final_viability': cert1.final_viability,
        'mean_viability': cert1.mean_viability,
    }

    cert2, _ = certify_constructor_persistence(
        'severe_drift',
        seq,
        [
            EpisodeCase('s1', substrate(0.20, 's1'), EnvironmentContext('harsh1', substrate_shift=0.08, transition_scale=0.72, energy_scale=1.32, integrity_drain=0.10, resource_delta=-0.12)),
            EpisodeCase('s2', substrate(0.23, 's2'), EnvironmentContext('harsh2', substrate_shift=0.10, transition_scale=0.70, energy_scale=1.36, integrity_drain=0.12, resource_delta=-0.15)),
            EpisodeCase('s3', substrate(0.17, 's3'), EnvironmentContext('harsh3', substrate_shift=0.09, transition_scale=0.74, energy_scale=1.30, integrity_drain=0.11, resource_delta=-0.14)),
            EpisodeCase('s4', substrate(0.21, 's4'), EnvironmentContext('harsh4', substrate_shift=0.07, transition_scale=0.76, energy_scale=1.28, integrity_drain=0.10, resource_delta=-0.13)),
        ],
        make_state(),
        recipes,
        model,
        cfg,
        seed=21,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    results['persistence_blocked_severe'] = {
        'status': cert2.status,
        'confidence': cert2.confidence,
        'success_rate': cert2.success_rate,
        'final_viability': cert2.final_viability,
        'negative_kp_episodes': cert2.negative_kp_episodes,
    }

    cert3, _ = certify_constructor_persistence(
        'low_diversity',
        seq,
        [
            EpisodeCase('d1', substrate(0.20, 'd1'), EnvironmentContext('same')),
            EpisodeCase('d2', substrate(0.21, 'd2'), EnvironmentContext('same', substrate_shift=0.0)),
            EpisodeCase('d3', substrate(0.19, 'd3'), EnvironmentContext('same')),
            EpisodeCase('d4', substrate(0.22, 'd4'), EnvironmentContext('same')),
        ],
        make_state(),
        recipes,
        model,
        cfg,
        seed=22,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    results['persistence_blocked_low_diversity'] = {
        'status': cert3.status,
        'context_diversity': cert3.context_diversity,
        'note': cert3.note,
    }

    unsafe = AtomicPlan(tasks['unsafe_claim_stable'])
    struct_cert = certify_family_impossibility(
        unsafe,
        [CounterfactualCase('f1', substrate(0.58, 'f1')), CounterfactualCase('f2', substrate(0.62, 'f2')), CounterfactualCase('f3', substrate(0.66, 'f3'))],
        theory,
        cfg,
    )
    results['family_impossibility_retained'] = {
        'status': struct_cert.status,
        'confidence': struct_cert.confidence,
        'shared_reason_classes': list(struct_cert.shared_reason_classes),
    }

    state = make_state()
    choice = ChoicePlan('choose_safe', (AtomicPlan(tasks['unsafe_claim_stable']), AtomicPlan(tasks['warm'])))
    out = execute_plan(choice, substrate(0.20, 'ch1'), state, recipes, model, cfg, np.random.default_rng(5))
    results['choice_avoids_impossible_retained'] = {
        'success': out.success,
        'chosen_recipe': out.chosen_recipe,
        'admissibility': out.admissibility,
    }
    return results


def main() -> None:
    print(json.dumps(run(), indent=2))


if __name__ == '__main__':
    main()

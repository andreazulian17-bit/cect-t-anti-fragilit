from __future__ import annotations

import json
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks, execute_plan
from cect_t_canonical_v4_2_clean_publication_ready.core.structural_theory import StructuralTheory, certify_family_impossibility
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import (
    EnvironmentContext,
    EpisodeCase,
    PersistenceRequirement,
    certify_constructor_persistence,
)
from cect_t_canonical_v4_2_clean_publication_ready.core.types import AtomicPlan, SeqPlan, CounterfactualCase, EngineConfig


def main() -> dict:
    cfg = EngineConfig()
    rng = np.random.default_rng(cfg.seed)
    model = make_temperature_domain()
    contracts = default_contracts()
    tasks = make_tasks(contracts)
    recipes = default_recipes()
    state = make_state()

    plan = SeqPlan('warm_then_stabilize', (AtomicPlan(tasks['warm']), AtomicPlan(tasks['stabilize'])))
    out = execute_plan(plan, substrate(0.20, 'demo'), state, recipes, model, cfg, rng)

    theory = StructuralTheory(model=model)
    unsafe = AtomicPlan(tasks['unsafe_claim_stable'])
    struct_cert = certify_family_impossibility(
        unsafe,
        [
            CounterfactualCase('u1', substrate(0.58, 'u1')),
            CounterfactualCase('u2', substrate(0.62, 'u2')),
            CounterfactualCase('u3', substrate(0.66, 'u3')),
        ],
        theory,
        cfg,
    )

    episodes = [
        EpisodeCase('e1', substrate(0.20, 'e1'), EnvironmentContext('nominal')),
        EpisodeCase('e2', substrate(0.22, 'e2'), EnvironmentContext('mild_shift', substrate_shift=0.02, resource_delta=-0.04)),
        EpisodeCase('e3', substrate(0.18, 'e3'), EnvironmentContext('mild_drag', transition_scale=0.98, energy_scale=1.02, integrity_drain=0.01)),
        EpisodeCase('e4', substrate(0.21, 'e4'), EnvironmentContext('nominal_plus', substrate_shift=0.01, resource_delta=-0.02)),
    ]
    persistence_cert, final_state = certify_constructor_persistence(
        'warm_stabilize_persistence',
        plan,
        episodes,
        make_state(),
        recipes,
        model,
        cfg,
        seed=11,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    result = {
        'plan_success': out.success,
        'plan_admissibility': out.admissibility,
        'plan_kp_delta': out.kp_delta,
        'held_contracts': state.held_contracts,
        'family_impossibility_status': struct_cert.status,
        'family_impossibility_confidence': struct_cert.confidence,
        'persistence_status': persistence_cert.status,
        'persistence_confidence': persistence_cert.confidence,
        'persistence_success_rate': persistence_cert.success_rate,
        'persistence_final_viability': persistence_cert.final_viability,
        'final_constructor_integrity': final_state.integrity,
        'final_constructor_kp': final_state.kp,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    main()

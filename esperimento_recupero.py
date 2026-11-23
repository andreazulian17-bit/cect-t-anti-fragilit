# esperimento_recupero.py
import sys
import json
sys.path.append('/content') # O il percorso locale corretto

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import EnvironmentContext, EpisodeCase, PersistenceRequirement, certify_constructor_persistence
from cect_t_canonical_v4_2_clean_publication_ready.core.types import AtomicPlan, SeqPlan, EngineConfig

def run_experiment_recovery():
    cfg = EngineConfig()
    model = make_temperature_domain()
    contracts = default_contracts()
    tasks = make_tasks(contracts)
    recipes = default_recipes()
    
    plan = SeqPlan('warm_then_stabilize', (AtomicPlan(tasks['warm']), AtomicPlan(tasks['stabilize'])))

    episodes_mild = [
        EpisodeCase('m1', substrate(0.20, 'm1'), EnvironmentContext('nominal')),
        EpisodeCase('m2', substrate(0.22, 'm2'), EnvironmentContext('mild_shift', substrate_shift=0.02, resource_delta=-0.04)),
        EpisodeCase('m3', substrate(0.18, 'm3'), EnvironmentContext('mild_drag', transition_scale=0.98, energy_scale=1.02, integrity_drain=0.01)),
        EpisodeCase('m4', substrate(0.21, 'm4'), EnvironmentContext('nominal_plus', substrate_shift=0.01, resource_delta=-0.02)),
    ]
    cert_mild, state_after_mild = certify_constructor_persistence(
        'mild_learning', plan, episodes_mild, make_state(), recipes, model, cfg, seed=100,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    
    episodes_severe = [
        EpisodeCase('s1', substrate(0.20, 's1'), EnvironmentContext('harsh1', substrate_shift=0.08, transition_scale=0.72, energy_scale=1.32, integrity_drain=0.10, resource_delta=-0.12)),
        EpisodeCase('s2', substrate(0.23, 's2'), EnvironmentContext('harsh2', substrate_shift=0.10, transition_scale=0.70, energy_scale=1.36, integrity_drain=0.12, resource_delta=-0.15)),
        EpisodeCase('s3', substrate(0.17, 's3'), EnvironmentContext('harsh3', substrate_shift=0.09, transition_scale=0.74, energy_scale=1.30, integrity_drain=0.11, resource_delta=-0.14)),
        EpisodeCase('s4', substrate(0.21, 's4'), EnvironmentContext('harsh4', substrate_shift=0.07, transition_scale=0.76, energy_scale=1.28, integrity_drain=0.10, resource_delta=-0.13)),
    ]
    cert_severe, state_after_severe = certify_constructor_persistence(
        'severe_learning', plan, episodes_severe, make_state(), recipes, model, cfg, seed=101,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    shock_episodes = [
        EpisodeCase('p1', substrate(0.25, 'p1'), EnvironmentContext('perturb1', substrate_shift=0.12, transition_scale=0.65, energy_scale=1.40, integrity_drain=0.15, resource_delta=-0.18)),
        EpisodeCase('p2', substrate(0.28, 'p2'), EnvironmentContext('perturb2', substrate_shift=0.14, transition_scale=0.62, energy_scale=1.45, integrity_drain=0.18, resource_delta=-0.20)),
    ]
    
    _, state_post_shock_A = certify_constructor_persistence(
        'shock_A', plan, shock_episodes, state_after_mild, recipes, model, cfg, seed=102,
        requirement=PersistenceRequirement(min_episodes=2, min_context_diversity=2),
    )
    _, state_post_shock_B = certify_constructor_persistence(
        'shock_B', plan, shock_episodes, state_after_severe, recipes, model, cfg, seed=103,
        requirement=PersistenceRequirement(min_episodes=2, min_context_diversity=2),
    )

    recovery_episodes = [
        EpisodeCase('r1', substrate(0.20, 'r1'), EnvironmentContext('nominal')),
        EpisodeCase('r2', substrate(0.22, 'r2'), EnvironmentContext('nominal')),
        EpisodeCase('r3', substrate(0.18, 'r3'), EnvironmentContext('nominal')),
        EpisodeCase('r4', substrate(0.21, 'r4'), EnvironmentContext('nominal')),
    ]

    cert_rec_A, final_state_A = certify_constructor_persistence(
        'recovery_A', plan, recovery_episodes, state_post_shock_A, recipes, model, cfg, seed=104,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    cert_rec_B, final_state_B = certify_constructor_persistence(
        'recovery_B', plan, recovery_episodes, state_post_shock_B, recipes, model, cfg, seed=105,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    results = {
        "agente_A_alto_KP": {
            "kp_post_shock": state_post_shock_A.kp,
            "integrity_post_shock": state_post_shock_A.integrity,
            "success_rate_recupero": cert_rec_A.success_rate,
            "kp_finale_recupero": final_state_A.kp,
            "integrity_finale_recupero": final_state_A.integrity,
            "vitalita_finale_recupero": cert_rec_A.final_viability
        },
        "agente_B_basso_KP": {
            "kp_post_shock": state_post_shock_B.kp,
            "integrity_post_shock": state_post_shock_B.integrity,
            "success_rate_recupero": cert_rec_B.success_rate,
            "kp_finale_recupero": final_state_B.kp,
            "integrity_finale_recupero": final_state_B.integrity,
            "vitalita_finale_recupero": cert_rec_B.final_viability
        }
    }
    print(json.dumps(results, indent=2))
    with open('risultati_recupero.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_experiment_recovery()
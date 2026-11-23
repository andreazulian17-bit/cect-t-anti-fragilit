# esperimento_moderato.py
import sys
import json
sys.path.append('/content') # O il percorso locale corretto

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import EnvironmentContext, EpisodeCase, PersistenceRequirement, certify_constructor_persistence
from cect_t_canonical_v4_2_clean_publication_ready.core.types import AtomicPlan, SeqPlan, EngineConfig

def run_experiment_moderato():
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

    perturbation_episodes = [
        EpisodeCase('p1', substrate(0.25, 'p1'), EnvironmentContext('mod_perturb1', substrate_shift=0.06, transition_scale=0.85, energy_scale=1.15, integrity_drain=0.08, resource_delta=-0.10)),
        EpisodeCase('p2', substrate(0.28, 'p2'), EnvironmentContext('mod_perturb2', substrate_shift=0.07, transition_scale=0.83, energy_scale=1.18, integrity_drain=0.09, resource_delta=-0.11)),
        EpisodeCase('p3', substrate(0.22, 'p3'), EnvironmentContext('mod_perturb3', substrate_shift=0.06, transition_scale=0.86, energy_scale=1.14, integrity_drain=0.08, resource_delta=-0.10)),
        EpisodeCase('p4', substrate(0.26, 'p4'), EnvironmentContext('mod_perturb4', substrate_shift=0.08, transition_scale=0.82, energy_scale=1.20, integrity_drain=0.09, resource_delta=-0.12)),
    ]
    
    cert_perturb_A, final_state_A = certify_constructor_persistence(
        'perturbation_A', plan, perturbation_episodes, state_after_mild, recipes, model, cfg, seed=102,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    cert_perturb_B, final_state_B = certify_constructor_persistence(
        'perturbation_B', plan, perturbation_episodes, state_after_severe, recipes, model, cfg, seed=103,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    results = {
        "agente_A_appreso_in_mite": {
            "kp_finale_apprendimento": state_after_mild.kp,
            "success_rate_apprendimento": cert_mild.success_rate,
            "kp_finale_perturbazione": final_state_A.kp,
            "success_rate_perturbazione": cert_perturb_A.success_rate,
            "vitalita_finale_perturbazione": cert_perturb_A.final_viability,
            "integrity_finale_perturbazione": final_state_A.integrity,
            "negative_kp_episodes": cert_perturb_A.negative_kp_episodes
        },
        "agente_B_appreso_in_severo": {
            "kp_finale_apprendimento": state_after_severe.kp,
            "success_rate_apprendimento": cert_severe.success_rate,
            "kp_finale_perturbazione": final_state_B.kp,
            "success_rate_perturbazione": cert_perturb_B.success_rate,
            "vitalita_finale_perturbazione": cert_perturb_B.final_viability,
            "integrity_finale_perturbazione": final_state_B.integrity,
            "negative_kp_episodes": cert_perturb_B.negative_kp_episodes
        }
    }
    print(json.dumps(results, indent=2))
    with open('risultati_esperimento_moderato.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_experiment_moderato()
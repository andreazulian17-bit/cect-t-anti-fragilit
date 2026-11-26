import os
import sys
import json
import numpy as np

# 1. Ci spostiamo fisicamente nella cartella del progetto
os.chdir('/content/progetto_ricerca')

# 2. Aggiungiamo la cartella corrente al path di Python
sys.path.append('.')

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import EnvironmentContext, EpisodeCase, PersistenceRequirement, certify_constructor_persistence
from cect_t_canonical_v4_2_clean_publication_ready.core.types import AtomicPlan, SeqPlan, EngineConfig

def run_experiment_curiosity():
    cfg = EngineConfig()
    model = make_temperature_domain()
    contracts = default_contracts()
    tasks = make_tasks(contracts)
    recipes = default_recipes()
    
    exploration_plan = SeqPlan(
        'explore_then_exploit',
        (
            AtomicPlan(tasks['warm']),
            AtomicPlan(tasks['stabilize']),
            AtomicPlan(tasks['cool'])
        )
    )

    episodes_explore = [
        EpisodeCase('e1', substrate(0.20, 'e1'), EnvironmentContext('nominal')),
        EpisodeCase('e2', substrate(0.15, 'e2'), EnvironmentContext('nominal')),
        EpisodeCase('e3', substrate(0.25, 'e3'), EnvironmentContext('nominal')),
        EpisodeCase('e4', substrate(0.10, 'e4'), EnvironmentContext('nominal')),
    ]
    
    cert_explore, state_after_explore = certify_constructor_persistence(
        'exploration_learning', exploration_plan, episodes_explore, make_state(), recipes, model, cfg, seed=200,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    shock_episodes = [
        EpisodeCase('s1', substrate(0.25, 's1'), EnvironmentContext('perturb1', substrate_shift=0.12, transition_scale=0.65, energy_scale=1.40, integrity_drain=0.15, resource_delta=-0.18)),
        EpisodeCase('s2', substrate(0.28, 's2'), EnvironmentContext('perturb2', substrate_shift=0.14, transition_scale=0.62, energy_scale=1.45, integrity_drain=0.18, resource_delta=-0.20)),
    ]
    
    _, state_post_shock = certify_constructor_persistence(
        'shock_explore', exploration_plan, shock_episodes, state_after_explore, recipes, model, cfg, seed=201,
        requirement=PersistenceRequirement(min_episodes=2, min_context_diversity=2),
    )

    recovery_episodes = [
        EpisodeCase('r1', substrate(0.20, 'r1'), EnvironmentContext('nominal')),
        EpisodeCase('r2', substrate(0.22, 'r2'), EnvironmentContext('nominal')),
        EpisodeCase('r3', substrate(0.18, 'r3'), EnvironmentContext('nominal')),
        EpisodeCase('r4', substrate(0.21, 'r4'), EnvironmentContext('nominal')),
    ]
    
    recovery_plan = SeqPlan('warm_then_stabilize', (AtomicPlan(tasks['warm']), AtomicPlan(tasks['stabilize'])))
    
    cert_rec, final_state = certify_constructor_persistence(
        'recovery_explore', recovery_plan, recovery_episodes, state_post_shock, recipes, model, cfg, seed=202,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )

    results = {
        "agente_curioso": {
            "kp_finale_apprendimento": state_after_explore.kp,
            "success_rate_apprendimento": cert_explore.success_rate,
            "integrity_post_shock": state_post_shock.integrity,
            "kp_finale_recupero": final_state.kp,
            "integrity_finale_recupero": final_state.integrity,
            "vitalita_finale_recupero": cert_rec.final_viability,
            "success_rate_recupero": cert_rec.success_rate
        }
    }
    
    print(json.dumps(results, indent=2))
    
    with open('/content/progetto_ricerca/risultati_curiosity.json', 'w') as f:
        json.dump(results, f, indent=2)

run_experiment_curiosity()
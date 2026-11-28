import os
import sys
import json
import numpy as np

os.chdir('/content/progetto_ricerca')
sys.path.append('.')

from cect_t_canonical_v4_2_clean_publication_ready.core.domain import make_temperature_domain, substrate
from cect_t_canonical_v4_2_clean_publication_ready.core.engine import default_contracts, default_recipes, make_state, make_tasks
from cect_t_canonical_v4_2_clean_publication_ready.core.persistence_theory import EnvironmentContext, EpisodeCase, PersistenceRequirement, certify_constructor_persistence
from cect_t_canonical_v4_2_clean_publication_ready.core.types import AtomicPlan, SeqPlan, CertifyPlan, EngineConfig

def run_controlled_experiment_fixed():
    cfg = EngineConfig()
    model = make_temperature_domain()
    contracts = default_contracts()
    tasks = make_tasks(contracts)
    recipes = default_recipes()

    # Episodi di apprendimento comuni
    episodes_learning = [
        EpisodeCase('m1', substrate(0.20, 'm1'), EnvironmentContext('nominal')),
        EpisodeCase('m2', substrate(0.22, 'm2'), EnvironmentContext('mild_shift', substrate_shift=0.02, resource_delta=-0.04)),
        EpisodeCase('m3', substrate(0.18, 'm3'), EnvironmentContext('mild_drag', transition_scale=0.98, energy_scale=1.02, integrity_drain=0.01)),
        EpisodeCase('m4', substrate(0.21, 'm4'), EnvironmentContext('nominal_plus', substrate_shift=0.01, resource_delta=-0.02)),
    ]

    # Episodi di shock comuni
    episodes_shock = [
        EpisodeCase('s1', substrate(0.25, 's1'), EnvironmentContext('perturb1', substrate_shift=0.12, transition_scale=0.65, energy_scale=1.40, integrity_drain=0.15, resource_delta=-0.18)),
        EpisodeCase('s2', substrate(0.28, 's2'), EnvironmentContext('perturb2', substrate_shift=0.14, transition_scale=0.62, energy_scale=1.45, integrity_drain=0.18, resource_delta=-0.20)),
    ]

    # --- GRUPPO A: CON CERTIFICAZIONE (eseguita in episodio dedicato) ---
    # Fase 1a: apprendimento standard (warm)
    plan_warm = AtomicPlan(tasks['warm'])
    cert_learn_A, state_A_after_warm = certify_constructor_persistence(
        'learn_A_warm', plan_warm, episodes_learning, make_state(), recipes, model, cfg, seed=400,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    
    # Fase 1b: certificazione esplicita (episodio separato, stessa storia operativa)
    # Usiamo un episodio "nominale" con un solo probe, per non alterare lo stato in modo diverso
    episodes_cert = [
        EpisodeCase('c1', substrate(0.20, 'c1'), EnvironmentContext('nominal')),
    ]
    plan_cert = CertifyPlan(
        name='certify_warm',
        body=AtomicPlan(tasks['warm']),
        probe_substrates=(substrate(0.20, 'p1'),),
        certificate_label='warm_cert',
        min_support=1, min_diversity=1, min_confidence=0.5
    )
    cert_cert, state_A_after_cert = certify_constructor_persistence(
        'cert_A', plan_cert, episodes_cert, state_A_after_warm, recipes, model, cfg, seed=400,
        requirement=PersistenceRequirement(min_episodes=1, min_context_diversity=1),
    )

    # CONTROLLO ESPLICITO: la certificazione deve esistere
    if 'warm_cert' not in state_A_after_cert.capabilities:
        print("ERRORE: warm_cert non è stata acquisita. Test interrotto.")
        return

    # Fase 2: shock
    cert_shock_A, state_A_post_shock = certify_constructor_persistence(
        'shock_A', plan_warm, episodes_shock, state_A_after_cert, recipes, model, cfg, seed=401,
        requirement=PersistenceRequirement(min_episodes=2, min_context_diversity=2),
    )

    # --- GRUPPO B: SENZA CERTIFICAZIONE ---
    cert_learn_B, state_B_after_warm = certify_constructor_persistence(
        'learn_B_warm', plan_warm, episodes_learning, make_state(), recipes, model, cfg, seed=400,
        requirement=PersistenceRequirement(min_episodes=4, min_context_diversity=2),
    )
    # B non esegue alcuna certificazione
    state_B_after_cert = state_B_after_warm

    cert_shock_B, state_B_post_shock = certify_constructor_persistence(
        'shock_B', plan_warm, episodes_shock, state_B_after_cert, recipes, model, cfg, seed=401,
        requirement=PersistenceRequirement(min_episodes=2, min_context_diversity=2),
    )

    # --- RISULTATI ---
    cap_used_during_shock = cert_shock_A.per_episode[0]['admissibility'] if cert_shock_A.per_episode else "unknown"
    
    results = {
        "gruppo_con_certificazione": {
            "capacita_acquisita": 'warm_cert' in state_A_after_cert.capabilities,
            "integrita_pre_shock": state_A_after_cert.integrity,
            "kp_pre_shock": state_A_after_cert.kp,
            "integrita_post_shock": state_A_post_shock.integrity,
            "kp_post_shock": state_A_post_shock.kp,
            "capacita_attiva_dopo_shock": 'warm_cert' in state_A_post_shock.capabilities
        },
        "gruppo_senza_certificazione": {
            "capacita_acquisita": False,
            "integrita_pre_shock": state_B_after_cert.integrity,
            "kp_pre_shock": state_B_after_cert.kp,
            "integrita_post_shock": state_B_post_shock.integrity,
            "kp_post_shock": state_B_post_shock.kp,
            "capacita_attiva_dopo_shock": False
        },
        "differenza_integrita_post_shock": state_A_post_shock.integrity - state_B_post_shock.integrity,
        "differenza_kp_post_shock": state_A_post_shock.kp - state_B_post_shock.kp,
    }

    print(json.dumps(results, indent=2))
    
    # Salva per il controllo
    with open('/content/progetto_ricerca/risultati_controllo_certificazione_fixed.json', 'w') as f:
        json.dump(results, f, indent=2)

    # Analisi dell'uso della capacità durante lo shock
    if 'warm_cert' in state_A_post_shock.capabilities:
        print("\nLa capacità warm_cert è sopravvissuta allo shock.")
    else:
        print("\nLa capacità warm_cert NON è sopravvissuta allo shock (revocata o scartata).")

run_controlled_experiment_fixed()
# cECT-T canonical v4.2 benchmark summary

## Key additions
- Persistent-constructor certification across multiple episodes and contexts.
- Explicit environment contexts with substrate/domain drift.
- Maintenance and recovery between episodes.

## Benchmark outcomes
### persistence_certified_mild
- **status**: certified_persistent
- **confidence**: 0.84125
- **success_rate**: 0.75
- **final_viability**: 0.75
- **mean_viability**: 0.83125

### persistence_blocked_severe
- **status**: not_certified
- **confidence**: 0.70356755
- **success_rate**: 0.5
- **final_viability**: 0.6634708000000001
- **negative_kp_episodes**: 1

### persistence_blocked_low_diversity
- **status**: not_certified
- **context_diversity**: 1
- **note**: insufficient context diversity

### family_impossibility_retained
- **status**: certified_impossible
- **confidence**: 0.9900000000000001
- **shared_reason_classes**: ['domain_law', 'relational']

### choice_avoids_impossible_retained
- **success**: True
- **chosen_recipe**: warm_specialist
- **admissibility**: possible

## Interpretation
- v4.2 keeps the structural-impossibility layer from v4.1 and adds a more formal notion of constructor persistence.
- The mild-context sequence certifies persistence; severe drift and low context diversity do not.
- This moves the canonical line toward a stronger theory of the constructor as a persistent entity, not just a one-shot executor.
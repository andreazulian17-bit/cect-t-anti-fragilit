# cECT-T Canonical v4.2

Canonical core for the current cECT-T line after v4.1 consolidation.

## What is new in v4.2

v4.2 adds a **persistent-constructor theory layer** on top of the canonical engine:

- `core/persistence_theory.py`
- certification of persistence across **episodes** rather than a single run
- explicit `EnvironmentContext`
- explicit `EpisodeCase`
- `PersistenceRequirement`
- `PersistenceCertificate`
- maintenance/recovery between episodes
- context-sensitive drift over substrate and domain parameters

This means the engine can now evaluate not only:

- whether a task/plan is executable,
- whether a family-level structural impossibility can be certified,
- whether capability/warranty certification is available,

but also whether the **same constructor remains viable across multiple episodes and contexts**.

## Package structure

- `core/types.py` — shared canonical data structures
- `core/domain.py` — toy domain definition
- `core/engine.py` — canonical execution engine
- `core/structural_theory.py` — family-level structural impossibility theory
- `core/persistence_theory.py` — persistence certification across episodes
- `runners/run_demo.py` — demo runner
- `runners/run_benchmarks.py` — benchmark runner
- `run_v4_2.py` — CLI entry point

## Run

```bash
python run_v4_2.py demo
python run_v4_2.py benchmarks
```

## Notes

This is still a toy-domain implementation, but it is meant to be a cleaner and more formal canonical base than the earlier chained version files.

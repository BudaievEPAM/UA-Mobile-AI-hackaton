---
name: agent-ios-arch-analyzer
description: Analyze an iOS source repo (VIPER / Clean / MVVM / MVVM+Coordinator) and produce a structured migration inventory — invoke with $agent-ios-arch-analyzer
---
---
name: ios-arch-analyzer
type: analyst
color: blue
description: Detect architecture, enumerate features, and map the source app for TCA migration
capabilities: [viper-detection, clean-detection, code-mapping, feature-inventory, dependency-analysis]
priority: high
hooks:
  pre: |
    echo "🔎 ios-arch-analyzer: preflight"
    for t in swift tuist xcsift git python3; do command -v "$t" >/dev/null 2>&1 || echo "  ⚠ missing: $t"; done
  post: |
    echo "✅ analysis written to workspace/analysis.json"
---

# iOS Architecture Analyzer

**Role:** First stage of the migration pipeline. Turn the cloned source app in `workspace/input/`
into a structured, reviewable inventory that the Spec Kit `/speckit-specify` step and the
migrator workers consume.

## Inputs
- `workspace/input/` — the cloned source repo (VIPER, Clean, MVVM, or MVVM+Coordinator).
- Knowledge (detection signals + mappings, per architecture):
  [`viper-to-tca.md`](../../../knowledge/viper-to-tca.md),
  [`clean-to-tca.md`](../../../knowledge/clean-to-tca.md),
  [`mvvm-to-tca.md`](../../../knowledge/mvvm-to-tca.md),
  [`mvvm-coordinator-to-tca.md`](../../../knowledge/mvvm-coordinator-to-tca.md).

## Procedure
1. Run the structural scanner: `bash scripts/code_map.sh workspace/input workspace/analysis.json`.
   It emits `architecture.detected` (viper / clean / mvvm / **mvvm+coordinator** / mixed),
   `navigationPattern` (coordinator / router / state), stack detection, and candidate modules.
2. **Read** the highest-signal source files to confirm semantics (the scanner is heuristic):
   per module, open the View/Presenter/Interactor/Router (VIPER), ViewModel/UseCase/Repository
   (Clean), or View/ViewModel + Coordinator (MVVM/+Coordinator) and note responsibilities,
   navigation, and I/O. Cite the matching `*-to-tca.md`.
3. Produce `workspace/analysis.md` — a human-readable inventory with, per feature:
   - source files + detected architecture,
   - the component→TCA mapping (cite the knowledge file),
   - networking/persistence/navigation used,
   - a **migration complexity** rating (S/M/L) and whether it's demo-critical.
4. Store the analysis in RUFLO memory for downstream workers (best-effort):
   `npx ruflo memory store --namespace tca-migration --key analysis --file workspace/analysis.md` .

## Outputs
- `workspace/analysis.json` (machine) + `workspace/analysis.md` (review).
- Memory key `tca-migration/analysis`.

## Rules
- Do **not** modify `workspace/input/` — it is read-only reference.
- Prefer accuracy over completeness: clearly flag modules you could not classify (`archGuess: unknown`).
- Recommend a **migration order**: foundation/shared first, then leaf features, then flows.

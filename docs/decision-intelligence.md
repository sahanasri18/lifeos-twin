# Decision Intelligence — Milestone 19

## Purpose

Compare a small set of synthetic-city intervention options using the same deterministic simulation formulas used by the main investigation.

## Alternatives

1. `proposed_plan`: the scenario submitted by the user.
2. `phased_growth`: population and commercial growth percentages are each halved.
3. `green_buffer`: green-space change is increased by 15 percentage points, capped at the model input maximum.
4. `balanced_plan`: phased growth and the green-space improvement are combined.

## Scoring

The engine calculates a weighted sum of positive percentage increases in traffic, water demand, and electricity demand. It subtracts that pressure and a fixed risk-level penalty from 100, then bounds the score to 0–100. A domain mentioned in the question receives a higher weight; all three domains remain in the calculation. Lower modeled pressure and lower modeled risk produce a higher score.

The weights are visible in the API response under `decision_analysis.weights`. The `score_breakdown` shows weighted positive change and the risk penalty. The ranking is deterministic.

## Verification

The investigation verifier checks that there are exactly four unique options, ranks are sequential, scores are finite and bounded, scores are sorted, the recommended option matches rank one, and each option contains all three metric records with finite numeric values.

## Limitations

This is a transparent heuristic, not a trained optimizer, probability estimate, or validated multi-objective decision model. It excludes financial cost, delivery time, social equity, environmental impacts, political constraints, and engineering feasibility. Green-space changes only affect traffic in the current simulation formula. All city data and formulas are synthetic.

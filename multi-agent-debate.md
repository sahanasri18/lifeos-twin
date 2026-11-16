# Multi-agent debate and consensus (Milestone 20)

## Flow

1. The decision engine produces four ranked scenario alternatives.
2. Traffic, water, and electricity specialists independently score all four alternatives using their own domain's modeled percentage change and a shared risk penalty.
3. Each specialist selects its highest-scoring option. Equal specialist scores are resolved by option ID for reproducibility.
4. The debate record includes two explanatory rounds and cross-domain challenges when specialists disagree.
5. Consensus is selected by highest vote count. A tie is resolved by the original overall decision score, then option ID.
6. Minority preferences and unresolved disagreements remain in the response rather than being hidden.

## API response

`specialist_debate` contains `agents`, `debate_rounds`, `challenges`, `votes`, `consensus_order`, `consensus_option_id`, `consensus_strength`, `dissent`, and `unresolved_disagreements`.

The `specialist_debate_consensus_valid` verification check validates the three expected specialists, complete option coverage, vote totals, consensus winner, and dissent count.

## Boundaries

The specialists are deterministic Python functions, not independent LLM calls or human expert opinions. The scores use synthetic simulation outputs. Debate does not change simulation results, and consensus is not a real infrastructure recommendation. The review does not account for project cost, equity, implementation feasibility, or calibrated engineering constraints.

# Agent Rules (`AGENTS.md`) — Token-Efficient Claims Engineering

These workspace rules follow the Google Cloud *Eleven Principles for Token Efficient Software Engineering* (Principle 2: *Use skills from the beginning* and Principle 9: *Iterate on rules in `AGENTS.md` or edit the skill instead of re-prompting*).

1. **Load skills on demand:** Use [`skills/cymbal-claims-adjudication/SKILL.md`](skills/cymbal-claims-adjudication/SKILL.md) when working on claim adjudication rules or prompts instead of pasting the full 20,000-token handbook into exploratory turns.
2. **Keep the tool declaration surface minimal:** Only pass the 4 adjudication tools (`get_policy`, `get_claims_history`, `screen_fraud`, `submit_decision`) in production runs (`R1–R5`). Every unused tool schema is re-billed on every turn.
3. **Normalize in code, not in prompts:** Normalize identifiers (`003009` → `POL-003009`) deterministically inside `Tools.norm_policy_id()` in [`run_experiment.py`](run_experiment.py) rather than adding corrective prompt instructions.
4. **Never write rules that contradict harness guards:** If `Tools.screen()` enforces `retry_budget=1`, never add a prompt instruction requiring a successful screening score before `submit_decision`. Contradictory instructions trigger expensive reasoning/thinking loops.
5. **Never hard-code GCP project IDs:** Read `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` from environment variables (`.env`).

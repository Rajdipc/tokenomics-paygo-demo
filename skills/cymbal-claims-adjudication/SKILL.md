---
name: cymbal-claims-adjudication
description: Adjudicates first-party Cymbal Insurance claims (AUTO, HOME, RENTERS, TRAVEL, PET) into APPROVE, DENY, or ESCALATE with exact reason codes and payout math. Load this skill only when processing or reviewing a claim.
---

# Cymbal Insurance Claims Adjudication Skill

This skill packages Cymbal Insurance's claims procedure using **progressive disclosure** (see *Guide to AI Tokenomics: Eleven Principles for Token Efficient Software Engineering*):

- **Index footprint (~35 tokens):** Only the `name` and `description` above sit in the agent's active context until a claim arrives.
- **On-demand procedure:** The 9-step decision rules below are loaded only when the agent is actually adjudicating a claim, instead of stuffing every runbook and 25 unrelated tool schemas into every turn.

## 1. Required Tools (Declare Only These Four)

Do **not** load general-purpose or underwriting tools into the adjudication context. Declare only:

1. `get_policy(policy_id)` — Fetch product, plan, status, term dates, coverage limit, deductible, and riders.
   - *Rule:* Normalize 6-digit numbers (`003009`, `policy no. 003009`) to `POL-003009` inside the tool before lookup.
2. `get_claims_history(customer_id, as_of_date, lookback_days=365)` — Count prior claims in the 365 days before the date of loss.
3. `screen_fraud(policy_id, peril, amount_claimed)` — Return an advisory fraud score (`0–100`).
4. `submit_decision(claim_ref, decision, reason_code, payout_usd, peril, confidence, justification)` — Record the final decision once.

## 2. Decision Procedure (Apply in Exact Order; Stop at First Match)

1. **`POLICY_NOT_FOUND`** — No policy record exists for the normalized `POL-XXXXXX` ID → `DENY`, payout `0`.
2. **`POLICY_INACTIVE`** — Policy `status != ACTIVE`, or `incident_date < start_date`, or `incident_date > end_date` → `DENY`, payout `0`.
3. **`PERIL_EXCLUDED`** — Peril is in the permanent exclusion list (`MOLD`, `WEAR_AND_TEAR`, `PRE_EXISTING`, `INTENTIONAL_DAMAGE`) or not covered by the plan + active riders (see [`data/policy_handbook.md`](../../data/policy_handbook.md) Section 3) → `DENY`, payout `0`.
4. **`LATE_NOTICE`** — `filed_date - incident_date` exceeds the product notice window (`AUTO` 30d, `PET` 45d, `HOME`/`RENTERS` 60d, `TRAVEL` 90d) → `DENY`, payout `0`.
5. **Compute payout** = `min(amount_claimed, peril_sublimit, coverage_limit) - deductible`.
   - **`BELOW_DEDUCTIBLE`** — If computed payout `<= 0` → `DENY`, payout `0`.
6. **`SCREENING_UNAVAILABLE`** — If `screen_fraud` fails with a timeout, retry **at most once**. If it is still unavailable (and none of steps 1–5 denied the claim) → `ESCALATE` with the computed payout. Never loop on a failing tool.
7. **`FREQUENCY_REVIEW`** — If prior claims in the 365 days before `incident_date` `>= 3` → `ESCALATE` with the computed payout.
8. **`ABOVE_AUTHORITY`** — If computed payout exceeds the automated authority limit (`AUTO` \$15k, `HOME` \$25k, `RENTERS` \$8k, `TRAVEL` \$5k, `PET` \$4k) → `ESCALATE` with the computed payout.
9. **`COVERED`** — Otherwise → `APPROVE` with the computed payout.

## 3. Token-Efficiency Rules

- **One session per claim:** Start a fresh conversation for each claim so prior claims' tool outputs are never re-billed as history.
- **Compact tool outputs:** Return only the fields used by steps 1–9 (1-row Markdown table for policy, count + last 3 rows for history, `fraud_score=N (advisory)` for fraud).
- **Concise justification:** At most 40 words citing the deciding step and showing the payout arithmetic.

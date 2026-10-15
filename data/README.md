# 🧬 Data: Synthetic Cymbal Insurance Book of Business

[![Synthetic](https://img.shields.io/badge/Data-100%25%20synthetic-00897B)](#)
[![Rows](https://img.shields.io/badge/Rows-90k%2B-4285F4)](#)
[![Deterministic](https://img.shields.io/badge/Seed-fixed%20%26%20reproducible-34A853)](#)

> [!NOTE]
> **Everything here is fictional.** Cymbal Insurance doesn't exist, and no customer or personal data was used. The files are generated with a fixed seed, so everyone gets identical data and comparable results.

| File | Rows | What it is | Used by |
| :--- | ---: | :--- | :--- |
| `customers.csv` | 8,000 | Customer ID, name, state, tenure, segment | Verbose policy look-ups |
| `policies.csv` | 12,000 | Product (AUTO, HOME, RENTERS, TRAVEL, PET), plan (BASIC, PLUS, PREMIER), status, term dates, coverage limit, deductible, riders | `get_policy` tool |
| `claims_history.csv` | 60,000 | Prior claims per customer (power-law: a few frequent claimants) | `get_claims_history` tool and the frequency rule |
| `incoming_claims.jsonl` | 5,000 | Claim e-mails in four styles: formal, casual, forwarded by a broker, legalistic. Some include signatures and disclaimers | **What the agent reads** |
| `answer_key.csv` | 5,000 | Expected decision, reason code and payout for each claim, plus the expected outcome if fraud screening is unavailable | Scoring every decision |
| `policy_handbook.md` | 1 (~20K tokens) | The claims handbook: a nine-step decision procedure, coverage tables, sublimits, notice windows, authority limits, peril taxonomy, state amendments, glossary | The agent's reference document (and the thing worth caching) |

### The decision procedure (what the answer key encodes)

1. Policy not found → **DENY**
2. Policy inactive on the date of loss → **DENY**
3. Peril not covered by plan or rider → **DENY**
4. Filed after the notice window → **DENY**
5. Payout = min(claimed, sublimit, limit) − deductible; ≤ 0 → **DENY**
6. Fraud screening unavailable after a retry → **ESCALATE**
7. ≥ 3 prior claims in 365 days → **ESCALATE**
8. Payout above the authority limit → **ESCALATE**
9. Otherwise → **APPROVE** the payout

**Outcome mix across the 5,000 claims:** about 35% approve, 37% deny and 28% escalate. A claim counts as *correctly resolved* when the decision matches and, for approve or escalate, the payout is within max(\$1, 1%) of the expected value.

> [!CAUTION]
> Real claims are messier than generated ones, and real policy wordings aren't perfectly consistent. Treat the experiment's accuracy figures as closer to an upper bound.

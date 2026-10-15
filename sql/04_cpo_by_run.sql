-- v_cpo_by_run: Cost per Outcome = everything it costs to get ONE claim resolved correctly.
--
--   CpO = (LLM tokens + explicit cache + tool calls + human review of escalations
--          + rework of wrong decisions) / correctly resolved claims
--
-- Non-token unit costs come from the cpo_params table (config/pricing.yaml ->
-- cpo_assumptions). They are illustrative - replace them with your own.
-- Chart (Visualization tab): Stacked bar, X = run_id,
--   Y = llm_usd_per_correct, tools_usd_per_correct, review_usd_per_correct, rework_usd_per_correct.
CREATE OR REPLACE VIEW tokenomics_demo.v_cpo_by_run AS
WITH p AS (
  SELECT
    MAX(IF(param = 'tool_call_usd', value, NULL)) AS tool_call_usd,
    MAX(IF(param = 'human_review_usd', value, NULL)) AS human_review_usd,
    MAX(IF(param = 'rework_usd', value, NULL)) AS rework_usd
  FROM tokenomics_demo.cpo_params
),
c AS (
  SELECT
    run_tag,
    run_id,
    COUNT(*) AS n_claims,
    COUNTIF(correct) AS n_correct,
    SUM(cost_usd) AS token_usd,
    SUM(tool_calls) AS tool_calls,
    COUNTIF(decision = 'ESCALATE') AS escalations,
    COUNTIF(NOT correct) AS wrong
  FROM tokenomics_demo.claims
  GROUP BY run_tag, run_id
),
r AS (
  SELECT run_tag, run_id, SUM(IFNULL(cache_storage_usd, 0) + IFNULL(cache_creation_usd, 0)) AS cache_usd
  FROM tokenomics_demo.runs
  GROUP BY run_tag, run_id
)
SELECT
  c.run_tag,
  c.run_id,
  c.n_claims,
  c.n_correct,
  SAFE_DIVIDE(c.token_usd + IFNULL(r.cache_usd, 0), c.n_correct) AS llm_usd_per_correct,
  SAFE_DIVIDE(c.tool_calls * p.tool_call_usd, c.n_correct) AS tools_usd_per_correct,
  SAFE_DIVIDE(c.escalations * p.human_review_usd, c.n_correct) AS review_usd_per_correct,
  SAFE_DIVIDE(c.wrong * p.rework_usd, c.n_correct) AS rework_usd_per_correct,
  SAFE_DIVIDE(
    c.token_usd + IFNULL(r.cache_usd, 0) + c.tool_calls * p.tool_call_usd
      + c.escalations * p.human_review_usd + c.wrong * p.rework_usd,
    c.n_correct) AS cpo_usd,
  SAFE_DIVIDE(c.token_usd + IFNULL(r.cache_usd, 0),
    c.token_usd + IFNULL(r.cache_usd, 0) + c.tool_calls * p.tool_call_usd
      + c.escalations * p.human_review_usd + c.wrong * p.rework_usd) AS llm_share_of_cpo
FROM c
CROSS JOIN p
LEFT JOIN r USING (run_tag, run_id);

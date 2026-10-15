-- v_run_summary: one row per run. The headline numbers of the post.
-- Chart (Visualization tab): Bar, X = run_label, Y = cost_per_claim_usd  -> the waterfall.
CREATE OR REPLACE VIEW tokenomics_demo.v_run_summary AS
WITH c AS (
  SELECT
    run_tag,
    run_id,
    COUNT(*) AS n_claims,
    COUNTIF(correct) AS n_correct,
    SUM(cost_usd) AS token_cost_usd,
    SUM(prompt_tokens) AS prompt_tokens,
    SUM(cached_tokens) AS cached_tokens,
    SUM(output_tokens) AS output_tokens,
    SUM(thoughts_tokens) AS thoughts_tokens,
    SUM(llm_calls) AS llm_calls,
    SUM(tool_calls) AS tool_calls,
    COUNTIF(decision = 'ESCALATE') AS n_escalated,
    COUNTIF(reviewed_by_frontier) AS n_reviewed_by_frontier,
    COUNTIF(error IS NOT NULL) AS n_errors,
    APPROX_QUANTILES(latency_ms, 100)[OFFSET(50)] AS p50_latency_ms,
    APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS p95_latency_ms,
    LOGICAL_OR(simulated) AS simulated
  FROM tokenomics_demo.claims
  GROUP BY run_tag, run_id
),
r AS (
  SELECT
    run_tag,
    run_id,
    ANY_VALUE(title) AS title,
    SUM(IFNULL(cache_storage_usd, 0) + IFNULL(cache_creation_usd, 0)) AS cache_usd
  FROM tokenomics_demo.runs
  GROUP BY run_tag, run_id
)
SELECT
  c.run_tag,
  c.run_id,
  CONCAT(c.run_id, ' ', REGEXP_EXTRACT(r.title, r'^[^:]+')) AS run_label,
  CASE c.run_id WHEN 'R0' THEN 0 WHEN 'R1' THEN 1 WHEN 'R2' THEN 2 WHEN 'R3' THEN 3
    WHEN 'R4U' THEN 4 WHEN 'R4G' THEN 5 WHEN 'R5' THEN 6 END AS run_order,
  r.title,
  c.n_claims,
  c.n_correct,
  SAFE_DIVIDE(c.n_correct, c.n_claims) AS accuracy,
  c.token_cost_usd,
  IFNULL(r.cache_usd, 0) AS cache_usd,
  c.token_cost_usd + IFNULL(r.cache_usd, 0) AS llm_cost_usd,
  SAFE_DIVIDE(c.token_cost_usd + IFNULL(r.cache_usd, 0), c.n_claims) AS cost_per_claim_usd,
  SAFE_DIVIDE(c.token_cost_usd + IFNULL(r.cache_usd, 0), c.n_correct) AS llm_cost_per_correct_claim_usd,
  SAFE_DIVIDE(c.prompt_tokens + c.output_tokens + c.thoughts_tokens, c.n_claims) AS tokens_per_claim,
  SAFE_DIVIDE(c.prompt_tokens, c.n_claims) AS input_tokens_per_claim,
  SAFE_DIVIDE(c.thoughts_tokens, c.n_claims) AS thinking_tokens_per_claim,
  SAFE_DIVIDE(c.cached_tokens, c.prompt_tokens) AS cached_ratio,
  SAFE_DIVIDE(c.llm_calls, c.n_claims) AS llm_calls_per_claim,
  SAFE_DIVIDE(c.n_reviewed_by_frontier, c.n_claims) AS frontier_review_rate,
  c.n_escalated,
  c.n_errors,
  c.p50_latency_ms,
  c.p95_latency_ms,
  c.simulated
FROM c
LEFT JOIN r USING (run_tag, run_id);

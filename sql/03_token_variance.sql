-- v_token_variance: how much the tokens of ONE claim vary within a run.
-- Averages hide the tail that blows budgets; forecast with p95, not the mean.
-- Chart (Visualization tab): Bar, X = run_id, Y = p50_tokens and p95_tokens.
CREATE OR REPLACE VIEW tokenomics_demo.v_token_variance AS
WITH per_claim AS (
  SELECT
    run_tag,
    run_id,
    claim_ref,
    complexity,
    prompt_tokens + output_tokens + thoughts_tokens AS tokens,
    cost_usd
  FROM tokenomics_demo.claims
)
SELECT
  run_tag,
  run_id,
  COUNT(*) AS n_claims,
  AVG(tokens) AS mean_tokens,
  APPROX_QUANTILES(tokens, 100)[OFFSET(10)] AS p10_tokens,
  APPROX_QUANTILES(tokens, 100)[OFFSET(50)] AS p50_tokens,
  APPROX_QUANTILES(tokens, 100)[OFFSET(90)] AS p90_tokens,
  APPROX_QUANTILES(tokens, 100)[OFFSET(95)] AS p95_tokens,
  MAX(tokens) AS max_tokens,
  SAFE_DIVIDE(APPROX_QUANTILES(tokens, 100)[OFFSET(95)],
              APPROX_QUANTILES(tokens, 100)[OFFSET(50)]) AS p95_to_p50_ratio,
  APPROX_QUANTILES(cost_usd, 100)[OFFSET(50)] AS p50_cost_usd,
  APPROX_QUANTILES(cost_usd, 100)[OFFSET(95)] AS p95_cost_usd,
  AVG(IF(complexity = 'simple', tokens, NULL)) AS mean_tokens_simple,
  AVG(IF(complexity = 'complex', tokens, NULL)) AS mean_tokens_complex
FROM per_claim
GROUP BY run_tag, run_id;

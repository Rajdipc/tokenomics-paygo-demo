-- v_lane_projection: what the SAME measured tokens would cost on each PayGo lane.
-- Only Standard PayGo was actually called. Priority, Flex and Batch are a re-pricing of
-- measured usage with public list prices - a projection, not a measurement. Latency,
-- throttling and success rates differ per lane and are not modelled here.
-- If a lane is not offered for a model (Gemini 4 Argon has no Flex PayGo), that model's calls
-- stay at the Standard price and lane_fully_available is FALSE.
-- Explicit-cache costs are excluded (they are lane-independent).
-- Chart (Visualization tab): Grouped bar, X = run_id, Y = usd_per_claim, series = lane.
CREATE OR REPLACE VIEW tokenomics_demo.v_lane_projection AS
WITH use_by_model AS (
  SELECT run_tag, run_id, model,
         SUM(prompt_tokens) AS prompt_tokens,
         SUM(cached_tokens) AS cached_tokens,
         SUM(output_tokens + thoughts_tokens) AS output_tokens
  FROM tokenomics_demo.calls
  GROUP BY run_tag, run_id, model
),
claim_counts AS (
  SELECT run_tag, run_id, COUNT(*) AS n_claims
  FROM tokenomics_demo.claims
  GROUP BY run_tag, run_id
),
lanes AS (
  SELECT lane FROM UNNEST(['standard', 'priority', 'flex', 'batch']) AS lane
),
priced AS (
  SELECT
    u.run_tag,
    u.run_id,
    l.lane,
    LOGICAL_AND(IFNULL(p.available, FALSE)) AS lane_fully_available,
    SUM((GREATEST(u.prompt_tokens - u.cached_tokens, 0)
           * IF(p.available, p.input_per_1m, s.input_per_1m)
         + u.cached_tokens
           * IF(p.available, IFNULL(p.cached_input_per_1m, p.input_per_1m), s.cached_input_per_1m)
         + u.output_tokens * IF(p.available, p.output_per_1m, s.output_per_1m)) / 1e6) AS usd
  FROM use_by_model AS u
  CROSS JOIN lanes AS l
  JOIN tokenomics_demo.pricing AS s ON s.model = u.model AND s.lane = 'standard'
  LEFT JOIN tokenomics_demo.pricing AS p ON p.model = u.model AND p.lane = l.lane
  GROUP BY u.run_tag, u.run_id, l.lane
)
SELECT
  priced.run_tag,
  priced.run_id,
  priced.lane,
  priced.lane_fully_available,
  priced.usd AS projected_token_usd,
  SAFE_DIVIDE(priced.usd, claim_counts.n_claims) AS usd_per_claim,
  SAFE_DIVIDE(priced.usd, std.usd) - 1 AS change_vs_standard
FROM priced
JOIN claim_counts USING (run_tag, run_id)
JOIN priced AS std
  ON std.run_tag = priced.run_tag AND std.run_id = priced.run_id AND std.lane = 'standard';

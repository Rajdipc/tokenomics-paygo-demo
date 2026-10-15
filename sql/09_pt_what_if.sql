-- 09_pt_what_if.sql - an offline SIZING model for Provisioned Throughput (PT). Nothing is bought.
-- Question: "If we reserved capacity equal to the pXX of our per-minute token demand, what share
-- of tokens would still spill over to PayGo, and how busy would the reservation be?"
-- Method: R5's measured average tokens per claim x a synthetic week of arrivals for a
-- hypothetical volume (weekday business-hours peak, quieter nights, weekends at 45%).
-- Edit the params CTE, then Run. Chart: Bar, X = sizing_percentile, Y = share_on_pt.
WITH params AS (
  SELECT 40000 AS claims_per_weekday, 'R5' AS run_id, 0.45 AS weekend_factor
),
shape AS (  -- relative arrivals per hour of day (0-23)
  SELECT hour, w
  FROM UNNEST([0.15, 0.10, 0.08, 0.08, 0.10, 0.20, 0.45, 0.80, 1.20, 1.50, 1.60, 1.55,
               1.40, 1.50, 1.60, 1.55, 1.40, 1.20, 0.90, 0.70, 0.55, 0.40, 0.30, 0.20]) AS w
  WITH OFFSET AS hour
),
per_claim AS (
  SELECT AVG(c.prompt_tokens + c.output_tokens + c.thoughts_tokens) AS tokens
  FROM tokenomics_demo.claims AS c, params AS p
  WHERE c.run_id = p.run_id AND c.error IS NULL
),
minutes AS (
  SELECT
    p.claims_per_weekday * IF(day >= 5, p.weekend_factor, 1)
      * s.w / (SELECT AVG(w) FROM shape) / 1440 * pc.tokens AS tpm
  FROM UNNEST(GENERATE_ARRAY(0, 6)) AS day
  CROSS JOIN shape AS s
  CROSS JOIN UNNEST(GENERATE_ARRAY(1, 60)) AS minute
  CROSS JOIN params AS p
  CROSS JOIN per_claim AS pc
),
caps AS (
  SELECT pct, APPROX_QUANTILES(tpm, 100)[OFFSET(pct)] AS cap
  FROM minutes, UNNEST([30, 50, 70, 90, 99]) AS pct
  GROUP BY pct
)
SELECT
  CONCAT('p', CAST(pct AS STRING)) AS sizing_percentile,
  ROUND(cap) AS reserved_tokens_per_minute,
  SUM(LEAST(tpm, cap)) / SUM(tpm) AS share_on_pt,
  1 - SUM(LEAST(tpm, cap)) / SUM(tpm) AS share_spilled_to_paygo,
  COUNTIF(tpm > cap) / COUNT(*) AS minutes_with_spillover,
  SUM(LEAST(tpm, cap)) / (COUNT(*) * cap) AS reserved_capacity_utilization
FROM minutes CROSS JOIN caps
GROUP BY pct, cap
ORDER BY pct;

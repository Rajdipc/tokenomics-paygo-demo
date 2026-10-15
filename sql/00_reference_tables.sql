-- 00_reference_tables.sql - run this once in BigQuery Studio (paste, then Run).
-- Creates the two small reference tables the views use:
--   pricing     public list prices per model and consumption lane (Gemini Platform pricing page,
--               as of 2026-10-15, global endpoint, prompts <= 200K tokens, USD per 1M tokens).
--               These are REGULAR list prices. Until 30 Nov 2026 (Gemini 4 Argon) and 31 Dec 2026
--               (Gemini 3.8 Flash) the pricing page shows promotional prices delivered as 50%
--               credits back; the billing export shows them as credits (net_cost in sql/07).
--   cpo_params  the non-token unit costs used for Cost per Outcome (illustrative - edit freely)
-- Only Standard PayGo is actually called by the demo; the other lanes RE-PRICE the measured tokens
-- (v_lane_projection). available = FALSE means the lane is not offered for that model
-- (Gemini 4 Argon has no Flex PayGo); NULL cached price = "N/A" on the pricing page.
-- All three models are generally available (GA).

CREATE OR REPLACE TABLE tokenomics_demo.pricing AS
SELECT * FROM UNNEST([
  STRUCT('gemini-4-argon' AS model, 'frontier' AS tier, 'standard' AS lane, TRUE AS available,
         4.00 AS input_per_1m, 0.20 AS cached_input_per_1m, 20.00 AS output_per_1m,
         CAST(NULL AS FLOAT64) AS cache_storage_per_1m_token_hour, DATE '2026-10-15' AS as_of),
  STRUCT('gemini-4-argon', 'frontier', 'priority', TRUE, 7.20, 0.36, 36.00, CAST(NULL AS FLOAT64), DATE '2026-10-15'),
  STRUCT('gemini-4-argon', 'frontier', 'flex', FALSE, CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), CAST(NULL AS FLOAT64), DATE '2026-10-15'),
  STRUCT('gemini-4-argon', 'frontier', 'batch', TRUE, 2.00, 0.10, 10.00, CAST(NULL AS FLOAT64), DATE '2026-10-15'),
  STRUCT('gemini-3.8-flash', 'flash', 'standard', TRUE, 1.50, 0.15, 7.50, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.8-flash', 'flash', 'priority', TRUE, 2.70, 0.27, 13.50, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.8-flash', 'flash', 'flex', TRUE, 0.75, 0.075, 3.75, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.8-flash', 'flash', 'batch', TRUE, 0.75, 0.075, 3.75, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.5-flash-lite', 'flash-lite', 'standard', TRUE, 0.30, 0.03, 2.50, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.5-flash-lite', 'flash-lite', 'priority', TRUE, 0.54, 0.054, 4.50, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.5-flash-lite', 'flash-lite', 'flex', TRUE, 0.15, 0.015, 1.25, 1.00, DATE '2026-10-15'),
  STRUCT('gemini-3.5-flash-lite', 'flash-lite', 'batch', TRUE, 0.15, 0.015, 1.25, 1.00, DATE '2026-10-15')
]);

CREATE OR REPLACE TABLE tokenomics_demo.cpo_params AS
SELECT * FROM UNNEST([
  STRUCT('tool_call_usd' AS param, 0.0004 AS value),   -- one internal API call
  STRUCT('human_review_usd', 12.0),                    -- senior adjuster reviews an escalation (10 min)
  STRUCT('rework_usd', 18.0)                           -- a human redoes a wrong decision
]);

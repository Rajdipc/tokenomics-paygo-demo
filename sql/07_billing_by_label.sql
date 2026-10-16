-- v_billing_by_label: the REAL invoice, broken down by the request labels the
-- runner attaches to every generateContent call (app, experiment, run, run_tag, step, tier).
--
-- Requirements: Cloud Billing export to BigQuery (detailed usage cost) enabled
-- and the table name below replaced with yours (Billing → Billing export shows it). Labels only reach billing on
-- PayGo traffic. Export data typically lands within hours, sometimes a day.
-- While the billing export backfill is still catching up to your run window,
-- this view automatically projects the SKU breakdown from tokenomics_demo.calls
-- + tokenomics_demo.pricing (with billing_source = 'CALLS_LEDGER_PENDING_EXPORT_BACKFILL').
-- Chart (Visualization tab): Bar, X = run_id, Y = net_cost, series = step.
CREATE OR REPLACE VIEW tokenomics_demo.v_billing_by_label AS
WITH export_rows AS (
  SELECT
    (SELECT value FROM UNNEST(labels) WHERE key = 'run_tag') AS run_tag,
    UPPER((SELECT value FROM UNNEST(labels) WHERE key = 'run')) AS run_id,
    (SELECT value FROM UNNEST(labels) WHERE key = 'step') AS step,
    (SELECT value FROM UNNEST(labels) WHERE key = 'tier') AS tier,
    service.description AS service,
    sku.description AS sku,
    SUM(usage.amount) AS usage_amount,
    ANY_VALUE(usage.unit) AS usage_unit,
    ROUND(SUM(cost), 4) AS gross_cost,
    ROUND(SUM(IFNULL((SELECT SUM(cr.amount) FROM UNNEST(credits) AS cr), 0)), 4) AS credits,
    ROUND(SUM(cost) + SUM(IFNULL((SELECT SUM(cr.amount) FROM UNNEST(credits) AS cr), 0)), 4) AS net_cost,
    'BILLING_EXPORT' AS billing_source
  FROM `billing_export.gcp_billing_export_resource_v1_XXXXXX_XXXXXX_XXXXXX`
  WHERE EXISTS (SELECT 1 FROM UNNEST(labels) WHERE key = 'experiment' AND value = 'tbom')
  GROUP BY run_tag, run_id, step, tier, service, sku
),
call_skus AS (
  SELECT
    c.run_tag,
    c.run_id,
    c.step,
    c.tier,
    'Vertex AI' AS service,
    CASE
      WHEN c.model = 'gemini-4-argon' THEN 'Gemini 4 Argon Text Input Prompts (Standard PayGo)'
      WHEN c.model = 'gemini-3.8-flash' THEN 'Gemini 3.8 Flash Text Input Prompts (Standard PayGo)'
      ELSE 'Gemini 3.5 Flash-Lite Text Input Prompts (Standard PayGo)'
    END AS sku,
    SUM(GREATEST(0, c.prompt_tokens - c.cached_tokens)) AS usage_amount,
    'tokens' AS usage_unit,
    SUM(GREATEST(0, c.prompt_tokens - c.cached_tokens) * p.input_per_1m / 1e6) AS raw_gross,
    c.model
  FROM tokenomics_demo.calls c
  JOIN tokenomics_demo.pricing p ON p.model = c.model AND p.lane = 'standard'
  GROUP BY c.run_tag, c.run_id, c.step, c.tier, c.model
  HAVING usage_amount > 0

  UNION ALL

  SELECT
    c.run_tag,
    c.run_id,
    c.step,
    c.tier,
    'Vertex AI' AS service,
    CASE
      WHEN c.model = 'gemini-4-argon' THEN 'Gemini 4 Argon Context Cache Read Input (Standard PayGo)'
      WHEN c.model = 'gemini-3.8-flash' THEN 'Gemini 3.8 Flash Context Cache Read Input (Standard PayGo)'
      ELSE 'Gemini 3.5 Flash-Lite Context Cache Read Input (Standard PayGo)'
    END AS sku,
    SUM(c.cached_tokens) AS usage_amount,
    'tokens' AS usage_unit,
    SUM(c.cached_tokens * p.cached_input_per_1m / 1e6) AS raw_gross,
    c.model
  FROM tokenomics_demo.calls c
  JOIN tokenomics_demo.pricing p ON p.model = c.model AND p.lane = 'standard'
  GROUP BY c.run_tag, c.run_id, c.step, c.tier, c.model
  HAVING usage_amount > 0

  UNION ALL

  SELECT
    c.run_tag,
    c.run_id,
    c.step,
    c.tier,
    'Vertex AI' AS service,
    CASE
      WHEN c.model = 'gemini-4-argon' THEN 'Gemini 4 Argon Text Output & Thinking (Standard PayGo)'
      WHEN c.model = 'gemini-3.8-flash' THEN 'Gemini 3.8 Flash Text Output & Thinking (Standard PayGo)'
      ELSE 'Gemini 3.5 Flash-Lite Text Output & Thinking (Standard PayGo)'
    END AS sku,
    SUM(c.output_tokens + c.thoughts_tokens) AS usage_amount,
    'tokens' AS usage_unit,
    SUM((c.output_tokens + c.thoughts_tokens) * p.output_per_1m / 1e6) AS raw_gross,
    c.model
  FROM tokenomics_demo.calls c
  JOIN tokenomics_demo.pricing p ON p.model = c.model AND p.lane = 'standard'
  GROUP BY c.run_tag, c.run_id, c.step, c.tier, c.model
  HAVING usage_amount > 0
),
fallback_rows AS (
  SELECT
    run_tag,
    run_id,
    step,
    tier,
    service,
    sku,
    usage_amount,
    usage_unit,
    ROUND(raw_gross, 4) AS gross_cost,
    ROUND(CASE WHEN model IN ('gemini-4-argon', 'gemini-3.8-flash') THEN -0.5 * raw_gross ELSE 0.0 END, 4) AS credits,
    ROUND(CASE WHEN model IN ('gemini-4-argon', 'gemini-3.8-flash') THEN 0.5 * raw_gross ELSE raw_gross END, 4) AS net_cost,
    'CALLS_LEDGER_PENDING_EXPORT_BACKFILL' AS billing_source
  FROM call_skus
)
SELECT * FROM export_rows
UNION ALL
SELECT * FROM fallback_rows
WHERE NOT EXISTS (SELECT 1 FROM export_rows);

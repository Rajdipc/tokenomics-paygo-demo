-- v_billing_by_label: the REAL invoice, broken down by the request labels the
-- runner attaches to every generateContent call (app, experiment, run, run_tag, step, tier).
--
-- Requirements: Cloud Billing export to BigQuery (detailed usage cost) enabled
-- and the table name below replaced with yours (Billing → Billing export shows it). Labels only reach billing on
-- PayGo traffic. Export data typically lands within hours, sometimes a day.
-- The billing export dataset must be in the same location as this dataset.
-- Chart (Visualization tab): Bar, X = run, Y = net_cost, series = step.
CREATE OR REPLACE VIEW tokenomics_demo.v_billing_by_label AS
SELECT
  (SELECT value FROM UNNEST(labels) WHERE key = 'run_tag') AS run_tag,
  UPPER((SELECT value FROM UNNEST(labels) WHERE key = 'run')) AS run_id,
  (SELECT value FROM UNNEST(labels) WHERE key = 'step') AS step,
  (SELECT value FROM UNNEST(labels) WHERE key = 'tier') AS tier,
  service.description AS service,
  sku.description AS sku,
  SUM(usage.amount) AS usage_amount,
  ANY_VALUE(usage.unit) AS usage_unit,
  SUM(cost) AS gross_cost,
  SUM(cost) + SUM(IFNULL((SELECT SUM(cr.amount) FROM UNNEST(credits) AS cr), 0)) AS net_cost
FROM `billing_export.gcp_billing_export_resource_v1_XXXXXX_XXXXXX_XXXXXX`
WHERE EXISTS (SELECT 1 FROM UNNEST(labels) WHERE key = 'experiment' AND value = 'tbom')
GROUP BY run_tag, run_id, step, tier, service, sku;

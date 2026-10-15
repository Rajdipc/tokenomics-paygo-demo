-- v_estimate_vs_invoice: runner estimate (measured tokens x list price) versus
-- what Cloud Billing actually charged, per run and step. A gap usually means
-- a price changed, a promotion/credit applied, or usage the runner did not see
-- (for example explicit-cache storage, which has no request label).
-- Chart (Visualization tab): Bar, X = run_id, Y = estimated_usd and billed_gross_usd.
CREATE OR REPLACE VIEW tokenomics_demo.v_estimate_vs_invoice AS
WITH est AS (
  SELECT run_tag, run_id, step, SUM(cost_usd) AS estimated_usd
  FROM tokenomics_demo.calls
  GROUP BY run_tag, run_id, step
),
billed AS (
  SELECT run_tag, run_id, step, SUM(gross_cost) AS billed_gross_usd, SUM(net_cost) AS billed_net_usd
  FROM tokenomics_demo.v_billing_by_label
  GROUP BY run_tag, run_id, step
)
SELECT
  est.run_tag,
  est.run_id,
  est.step,
  est.estimated_usd,
  billed.billed_gross_usd,
  billed.billed_net_usd,
  SAFE_DIVIDE(billed.billed_gross_usd - est.estimated_usd, est.estimated_usd) AS invoice_gap_ratio
FROM est
LEFT JOIN billed USING (run_tag, run_id, step);

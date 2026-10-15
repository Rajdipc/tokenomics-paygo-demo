-- v_loop_guard: a flaky dependency, with and without harness guardrails (R4U vs R4G),
-- split into the claims that hit the fault and the healthy ones.
-- Chart (Visualization tab): Bar, X = run_id, Y = avg_cost_usd, filter fault_injected = true.
CREATE OR REPLACE VIEW tokenomics_demo.v_loop_guard AS
SELECT
  run_tag,
  run_id,
  fault_injected,
  COUNT(*) AS n_claims,
  AVG(llm_calls) AS avg_llm_calls,
  MAX(llm_calls) AS max_llm_calls,
  AVG(tool_failures) AS avg_tool_failures,
  AVG(cost_usd) AS avg_cost_usd,
  MAX(cost_usd) AS max_cost_usd,
  AVG(prompt_tokens + output_tokens + thoughts_tokens) AS avg_tokens,
  SAFE_DIVIDE(COUNTIF(correct), COUNT(*)) AS accuracy,
  COUNTIF(guard_tripped) AS guard_trips,
  COUNTIF(reason_code = 'LOOP_GUARD') AS forced_escalations,
  COUNTIF(error IS NOT NULL) AS errors
FROM tokenomics_demo.claims
WHERE run_id IN ('R4U', 'R4G', 'R5')
GROUP BY run_tag, run_id, fault_injected;

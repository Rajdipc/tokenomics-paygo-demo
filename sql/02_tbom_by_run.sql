-- v_tbom_by_run: the Token Bill of Materials per run, in tokens AND dollars per claim.
-- Chart (Visualization tab): Stacked bar, X = run_id, Y = usd_per_claim, series = line_item.
--
-- Input line items share the call's input cost in proportion to their tokens
-- (cached tokens lower the blended input rate of every input line item).
-- Thinking and visible output are billed at the output rate.
CREATE OR REPLACE VIEW tokenomics_demo.v_tbom_by_run AS
WITH priced AS (
  SELECT
    c.*,
    (GREATEST(c.prompt_tokens - c.cached_tokens, 0) * p.input_per_1m
      + c.cached_tokens * IFNULL(p.cached_input_per_1m, p.input_per_1m)) / 1e6 AS input_usd,
    c.output_tokens * p.output_per_1m / 1e6 AS output_usd,
    c.thoughts_tokens * p.output_per_1m / 1e6 AS thinking_usd
  FROM tokenomics_demo.calls AS c
  JOIN tokenomics_demo.pricing AS p
    ON p.model = c.model AND p.lane = 'standard'
),
items AS (
  SELECT run_tag, run_id, claim_ref, 'system_prompt' AS line_item,
         tbom_system_prompt AS tokens, SAFE_DIVIDE(tbom_system_prompt, prompt_tokens) * input_usd AS usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'handbook', tbom_handbook,
         SAFE_DIVIDE(tbom_handbook, prompt_tokens) * input_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'tool_schemas', tbom_tool_schemas,
         SAFE_DIVIDE(tbom_tool_schemas, prompt_tokens) * input_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'history', tbom_history,
         SAFE_DIVIDE(tbom_history, prompt_tokens) * input_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'tool_results', tbom_tool_results,
         SAFE_DIVIDE(tbom_tool_results, prompt_tokens) * input_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'claim_input', tbom_claim_input,
         SAFE_DIVIDE(tbom_claim_input, prompt_tokens) * input_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'thinking', thoughts_tokens, thinking_usd FROM priced
  UNION ALL SELECT run_tag, run_id, claim_ref, 'visible_output', output_tokens, output_usd FROM priced
)
SELECT
  run_tag,
  run_id,
  line_item,
  SUM(tokens) / COUNT(DISTINCT claim_ref) AS tokens_per_claim,
  SUM(IFNULL(usd, 0)) / COUNT(DISTINCT claim_ref) AS usd_per_claim,
  SAFE_DIVIDE(SUM(tokens), SUM(SUM(tokens)) OVER (PARTITION BY run_tag, run_id)) AS share_of_tokens
FROM items
GROUP BY run_tag, run_id, line_item;

# Medium assets

PNG versions of everything Medium can't render (tables and Mermaid diagrams), numbered in the
order they appear in the post. Each one matches a 🖼️ callout in
`The Token Bill of Materials_ … (Medium).md` and in `medium_publisher.html`.

Rendered by `author_tools/render_medium_assets.py` (headless Chrome, 2x scale). The result
tables (5 and 7) read `tokenomics-paygo-demo/results/blog-1015/summary.json` only, so every
number in them comes from the real run.

| File | Blog section | Source in the blog | Numbers from |
|---|---|---|---|
| `table_1_four_meters.png` | The four meters on an AI bill | Markdown table | Static text |
| `table_1b_extensions.png` | Where the money goes: Layer 4 (Harness) | Markdown table | Static text (*Eleven Principles* + repo `SKILL.md` / `AGENTS.md`) |
| `diagram_1_apigee_gateway.png` | The gateway layer: Apigee | Mermaid diagram | Static text |
| `table_2_vanity_vs_outcome.png` | From cost to value | Markdown table | Static text |
| `table_3_data.png` | About the data (it's all synthetic) | Markdown table | Generated dataset sizes |
| `diagram_2_architecture.png` | The setup: one script, everything else in the console | Mermaid diagram | Static text |
| `table_4_models_prices.png` | Five designs, one agent | Markdown table | Pricing page, 15 Oct 2026 |
| `table_5_scoreboard.png` | The results | Markdown table | Real run `blog-1015` |
| `table_6_consumption_options.png` | Choosing how to pay for the tokens | Markdown table | Static text (documentation) |
| `table_7_pt_what_if.png` | Choosing how to pay for the tokens | Markdown table | Real run `blog-1015` + `sql/09` sizing model |
| `diagram_3_lane_decision_tree.png` | Choosing how to pay for the tokens | Mermaid diagram | Static text |


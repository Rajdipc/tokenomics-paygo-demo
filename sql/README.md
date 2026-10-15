# 📊 SQL: Paste into BigQuery Studio

[![BigQuery](https://img.shields.io/badge/BigQuery-Studio-669DF6?logo=googlebigquery&logoColor=white)](https://docs.cloud.google.com/bigquery/docs/running-queries)
[![No scripts](https://img.shields.io/badge/Console-paste%20%26%20run-FBBC04)](#)

Every file is plain GoogleSQL. Open **BigQuery Studio**, click **+** for a new query tab, paste a file, and click **Run**. The files assume a dataset called `tokenomics_demo`; find and replace it if you used another name.

| Order | File | Creates | Needs |
| :---: | :--- | :--- | :--- |
| 0 | `schemas/calls.json`, `claims.json`, `runs.json` | Schemas to paste into **Create table → Edit as text** when uploading the JSONL results | `results/<run_tag>/*.jsonl` |
| 1 | `00_reference_tables.sql` | Tables `pricing` (list prices per model and lane) and `cpo_params` (cost-per-outcome assumptions) | The dataset |
| 2 | `01_run_summary.sql` | `v_run_summary`: cost per claim, accuracy, tokens, cached share | Uploaded tables |
| 3 | `02_tbom_by_run.sql` | `v_tbom_by_run`: the Token Bill of Materials in tokens and \$ | `pricing` |
| 4 | `03_token_variance.sql` | `v_token_variance`: p50 vs p95 per claim | Uploaded tables |
| 5 | `04_cpo_by_run.sql` | `v_cpo_by_run`: cost per correctly resolved claim | `cpo_params` |
| 6 | `05_lane_projection.sql` | `v_lane_projection`: the same tokens re-priced on Priority, Flex and Batch | `pricing` |
| 7 | `06_loop_guard.sql` | `v_loop_guard`: R4U vs R4G on the faulty claims | Uploaded tables |
| 8 | `07_billing_by_label.sql` | `v_billing_by_label`: the real invoice by request label | Cloud Billing export (edit the table name) |
| 9 | `08_estimate_vs_invoice.sql` | `v_estimate_vs_invoice`: the script's estimate vs Cloud Billing | Step 8 |
| 10 | `09_pt_what_if.sql` | A query (not a view) that sizes a hypothetical Provisioned Throughput reservation | R5 results |

> [!TIP]
> After running a query, open the **Visualization** tab under the results to chart it. Each file's header comment suggests a chart type and fields. [`RUNBOOK.md`](../RUNBOOK.md#8-build-the-charts-bigquery-studio--visualization-tab) lists the exact chart queries used in the blog post.

> [!NOTE]
> Prices in `00_reference_tables.sql` are regular list prices as of 15 Oct 2026. Edit them if prices change, and edit `cpo_params` to use your own review and rework costs.

# 📸 Screenshot & Evidence Guide: Step-by-Step Capture & Highlighting Instructions

This guide tells you **where to click**, **what to frame**, **what to highlight (draw a box or arrow around)** as visual proof for each claim in the blog post, and **what to redact** before publishing on Medium.

- **Save path:** Save every screenshot into `images/` (next to the blog file) using the exact filename listed below.
- **Browser setup:** Use a browser window ~1440 px wide, light theme, 100% zoom so text stays crisp in Medium.
- **Redaction rule:** Before uploading to Medium, cover your **GCP project ID (`<YOUR_PROJECT_ID>`)**, **project number**, **billing account ID**, and (if you prefer not to show it publicly) your **email address (`rajdipch@google.com`)** using a solid opaque rectangle.
- **Run tag used for the published numbers:** **`blog-1015`** (BigQuery dataset `tokenomics_demo` in project `<YOUR_PROJECT_ID>`).

---

## 💡 Understanding Guardrails First: Cloud Billing Budgets (`E2`) vs. Cloud Monitoring Token-Burn Alerts (`E3`)

A common point of confusion is why an AI workload needs **both** a **Cloud Billing Budget (`E2`)** and a **Cloud Monitoring Token-Burn Alert (`E3`)**. They operate on completely different data sources, timescales, and failure modes:

| Dimension | 1. Cloud Billing Budget (`E2` · `c03_budget.png`) | 2. Cloud Monitoring Token-Burn Alert (`E3` · `c04_alert_policy.png`) |
| :--- | :--- | :--- |
| **Where it lives** | **Console → Billing → Budgets & alerts** | **Console → Monitoring → Alerting** |
| **What it measures** | **Cumulative monthly dollars (`$ USD`)** billed across the entire billing month | **Real-time tokens per minute (`token_count`)** over a 60-second rolling window |
| **How fast it reacts** | **Hours** (billing usage is aggregated and exported several times a day) | **60–120 seconds** (streams live from `aiplatform.googleapis.com` telemetry) |
| **Who it is for** | **FinOps & Finance** ("Are we tracking toward our $100 monthly budget?") | **On-call Engineers / SRE** ("Is an agent stuck in a runaway retry loop *right now*?") |
| **Does it stop traffic?** | **No** — sends email notifications at 50%, 90%, 100% actual & 100% forecasted spend | **No** — opens a Cloud Monitoring Incident and emails `rajdipch@google.com` immediately; your harness loop guards (`max_same_call=2`, `max_calls=8`, `--max-usd`) stop the code |
| **What happens in our demo** | Tracks total demo spend (~$11.98 net / ~$25 list price against a $100 budget) | Stays green during healthy `R5` (**645,546 tokens/min** peak), then **fires during `R4U`** when unguarded retry loops spike token burn to **905,391 tokens/min** (breaching the **750,000 tokens/min** threshold!) |

---

## ⏱️ Exact Run Windows for `blog-1015` (Use These in Monitoring, Trace & Model Observability)

All runs were executed on **15 Oct 2026** under `run_tag = blog-1015` (from `tokenomics-paygo-demo/results/blog-1015/runs.jsonl`):

| Run | Design | Claims | Accuracy | $/claim | Start (UTC) | End (UTC) | Start (IST) | End (IST) |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- | :--- | :--- |
| **R0** | Baseline: one frontier agent, 25 tools, 3 claims/chat | 50 | 100.0% | $0.2196 | `08:08:50` | `08:22:03` | `13:38:50` | `13:52:03` |
| **R1** | Trim the TBOM (3 tools via skill, compact output, 1 claim/chat) | 50 | 100.0% | $0.1363 | `09:28:21` | `09:35:36` | `14:58:21` | `15:05:36` |
| **R2** | Tier the models (Flash-Lite → 3.8 Flash → 4 Argon cascade) | 50 | 100.0% | $0.0600 | `09:35:36` | `09:41:27` | `15:05:36` | `15:11:27` |
| **R3** | Cache the prefix (explicit cache on Flash, implicit on Argon) | 50 | 100.0% | $0.0233 | `09:41:27` | `09:45:44` | `15:11:27` | `15:15:44` |
| **R5** | Production: R3 + loop guards on healthy dependencies | 50 | 100.0% | $0.0233 | `09:45:44` | `09:50:33` | `15:15:44` | `15:20:33` |
| **R4U** | Failure scenario (20% fraud timeout), **NO loop guards** | 40 | 87.5% | $0.0363 | `09:50:35` | `09:56:58` | `15:20:35` | `15:26:58` |
| **R4G** | Failure scenario (20% fraud timeout), **WITH loop guards** | 40 | 100.0% | $0.0253 | `09:56:58` | `10:01:02` | `15:26:58` | `15:31:02` |

- **Best window for `R1 → R5 → R4U → R4G` (Alerting & Model Observability):** **`09:28 UTC – 10:02 UTC`** (**`14:58 IST – 15:32 IST`** on 15 Oct 2026).
- **Best window for `R5` vs `R4U` vs `R4G` (Alert firing screenshot `E5`):** **`09:45 UTC – 10:02 UTC`** (**`15:15 IST – 15:32 IST`** on 15 Oct 2026).

---

## 📋 Master Checklist of All 16 Evidence Screenshots

| Step | Blog ID | Target File | Console Surface | Status / Notes |
| :---: | :---: | :--- | :--- | :--- |
| **1** | **E2** | `images/c03_budget.png` | Cloud Billing → Budgets & alerts | Create/open the $100 monthly budget |
| **2** | **E3** | `images/c04_alert_policy.png` | Cloud Monitoring → Alerting → Policies | **Already created** in `<YOUR_PROJECT_ID>` (`TBOM demo - Gemini token burn rate`, email `rajdipch@google.com`) |
| **3** | **E14** | `images/c05_billing_export.png` | Cloud Billing → Billing export | Detailed usage cost export settings |
| **4** | **E4** | `images/s02_run_r0_r5.png` | Cloud Shell / Terminal | Saved in `results/blog-1015/run_log.txt` |
| **5** | **E5** | `images/s11_alert.png` | Cloud Monitoring → Alerting | **Alert fired!** `R4U` peaked at **905,391 tokens/min** (above 750,000 threshold) at `09:52–09:55 UTC` (`15:22–15:25 IST`) |
| **6** | **E6** | `images/s03_trace.png` | Cloud Trace → Trace explorer | Verified `R5` trace ID ready to paste |
| **7** | **E7** | `images/s04_model_observability.png` | Agent Platform (Gemini Platform) → Dashboard | Model observability throughput by model |
| **8** | **E8** | `images/c06_upload_table.png` | BigQuery → Create table (Upload) | Upload `calls.jsonl` with `sql/schemas/calls.json` |
| **9** | **E9** | `images/s05_bq_waterfall.png` | BigQuery Studio → Visualization tab | Cost waterfall (`R0 → R5`: `$0.220 → $0.023`) |
| **10** | **E10** | `images/s06_bq_tbom.png` | BigQuery Studio → Visualization tab | Stacked TBOM (`R0` vs `R5` line items) |
| **11** | **E11** | `images/s07_bq_variance.png` | BigQuery Studio → Visualization tab | `p50` vs `p95` token variance across runs |
| **12** | **E12** | `images/s09_bq_lanes.png` | BigQuery Studio → Visualization tab | Consumption lanes (`Standard`, `Priority`, `Flex`, `Batch`) |
| **13** | **E13** | `images/s08_bq_cpo.png` | BigQuery Studio → Visualization tab | Cost per Outcome (`$2.86` in `R0` → `$2.66` in `R5`) |
| **14** | **E15** | `images/s13_billing_labels.png` | BigQuery Studio → Results grid | `v_billing_by_label` (once billing export populates) |
| **15** | **E16** *(opt)* | `images/c09_apigee_policies.png` | Apigee → Proxy development | Optional: only if you deploy the Apigee extension |
| **16** | **E17** *(opt)* | `images/s14_apigee_analytics.png` | Apigee → Analytics → API metrics | Optional: only if you deploy the Apigee extension |

---

## 🔍 Step-by-Step Instructions: How to Capture & What to Highlight

---

### Step 1 — Cloud Billing Budget (`E2`) → `images/c03_budget.png`

- **🎯 What this proves in the blog:** You established a monthly financial guardrail with multi-stage actual (`50%`, `90%`, `100%`) and forecasted (`100%`) email alerts before running any agent workload.
- **🧭 Step-by-step Console clicks:**
  1. Open [Cloud Billing → Budgets & alerts](https://console.cloud.google.com/billing) in the Google Cloud Console and select your billing account.
  2. Click **+ CREATE BUDGET** in the top bar (or click your existing demo budget to edit/view it).
  3. **Step 1 (Scope):**
     - **Name:** `TBOM Demo - Monthly Budget`
     - **Time range:** `Monthly`
     - **Projects:** Select `<YOUR_PROJECT_ID>`
     - **Services:** `All services` → click **Next**.
  4. **Step 2 (Amount):**
     - **Budget type:** `Specified amount`
     - **Target amount:** `$100.00` → click **Next**.
  5. **Step 3 (Actions):**
     - Add threshold rules at **`50%` ($50.00 Actual)**, **`90%` ($90.00 Actual)**, **`100%` ($100.00 Actual)**, and **`100%` ($100.00 Forecasted)**.
     - Under **Manage notifications**, check **Email alerts to billing admins and users** (or link the Cloud Monitoring email channel for `rajdipch@google.com`).
  6. Click **Finish**, then click into `TBOM Demo - Monthly Budget` so the summary view and threshold rules are visible on one screen.
- **🖼️ What to frame:** The budget detail page showing the budget name, project scope, `$100.00` target amount, the 4 threshold rows (`50%`, `90%`, `100%` actual + `100%` forecasted), and the email notification setting.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The **`$100.00` Target amount** and **`Monthly`** scope.
  2. Box 2: The **four threshold rows** (`50%`, `90%`, `100% Actual`, and `100% Forecasted`).
  3. Box 3: The **Email notification** checkbox showing alerts are routed to your mailbox.
- **🔒 What to redact:** Billing Account ID in the top breadcrumb/sidebar and project ID `<YOUR_PROJECT_ID>`.

---

### Step 2 — Cloud Monitoring Token-Burn Rate Alert Policy (`E3`) → `images/c04_alert_policy.png`

> ✅ **Already configured for you in `<YOUR_PROJECT_ID>`!**
> - **Policy Name:** `TBOM demo - Gemini token burn rate` (ID: `8458942289128046040`)
> - **Metric:** `aiplatform.googleapis.com/publisher/online_serving/token_count` (`1 min` rolling sum across all models)
> - **Threshold:** `> 750,000` tokens/minute
> - **Notification Channel:** Email `rajdipch@google.com` (`TBOM Demo Alert Email (rajdipch)`, ID: `6158932876965368063`)

- **🎯 What this proves in the blog:** Unlike a monthly billing budget, this operational alert watches live Gemini token consumption per minute and emails `rajdipch@google.com` within 60 seconds if an unguarded agent loop spikes token burn above `750,000 tokens/min`.
- **🧭 Step-by-step Console clicks:**
  1. Open [Cloud Monitoring → Alerting](https://console.cloud.google.com/monitoring/alerting?project=<YOUR_PROJECT_ID>).
  2. Under the **Policies** section, click **`TBOM demo - Gemini token burn rate`** (or click **Edit** `✏️` at the top of the policy page to show the full condition builder and notification channel in one view).
- **🖼️ What to frame:** The policy configuration view showing the policy name (`TBOM demo - Gemini token burn rate`), the condition (`Gemini token burn rate > 750k tokens/min`), the metric (`aiplatform.googleapis.com/publisher/online_serving/token_count`, `1 min` rolling sum), and the **Notifications** section showing `rajdipch@google.com`.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: Metric **`Publisher Model - Token count`** (`aiplatform.googleapis.com/publisher/online_serving/token_count`) with **`1 min` sum**.
  2. Box 2: Threshold **`Above 750,000`**.
  3. Box 3: Notification channel **`TBOM Demo Alert Email (rajdipch)` / `rajdipch@google.com`**.
- **🔒 What to redact:** Project ID `<YOUR_PROJECT_ID>` (keep `rajdipch@google.com` visible if you want to show it in the blog, or redact the username portion if you prefer).

---

### Step 3 — Cloud Billing Export to BigQuery (`E14`) → `images/c05_billing_export.png`

- **🎯 What this proves in the blog:** Exporting Detailed Usage Cost to BigQuery is what turns the opaque monthly PDF invoice into a queryable table where every Gemini API call can be grouped by `labels.run`, `labels.step`, and `labels.tier`.
- **🧭 Step-by-step Console clicks:**
  1. Open [Cloud Billing → Billing export](https://console.cloud.google.com/billing/export) in the Console.
  2. Stay on the **BigQuery export** tab.
  3. Locate the **Detailed usage cost** card (if not enabled, click **Edit settings**, select your project and dataset `billing_export` in `US`, and click **Save**).
- **🖼️ What to frame:** The **Detailed usage cost** card showing the green **Enabled** checkmark, the target project, and the `billing_export` dataset name.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The **Detailed usage cost → Enabled** status badge.
  2. Box 2: The **Dataset name (`billing_export`)** where the `gcp_billing_export_resource_v1_*` table is written.
- **🔒 What to redact:** Billing Account ID and Project ID.

---

### Step 4 — Cloud Shell / Terminal Run Summary (`E4`) → `images/s02_run_r0_r5.png`

- **🎯 What this proves in the blog:** A single command (`run_experiment.py`) executed all designs on the exact same synthetic claims, printing live accuracy, tokens/claim, cache hit percentage, and list-price USD/claim.
- **🧭 Step-by-step clicks:**
  1. In Cloud Shell or your terminal, run:
     ```bash
     cat /usr/local/google/home/rajdipch/my-projects/blog/ai-tokenomics-tbom/tokenomics-paygo-demo/results/blog-1015/run_log.txt
     ```
  2. Resize the terminal window so each line fits on one row without wrapping:
     ```text
     run_tag=blog-1015  claims=50  runs=['R0', 'R1', 'R2', 'R3', 'R5']  ->  .../results/blog-1015
     R0   Baseline: one frontier agent does it all claims= 50 accuracy=100.0% tokens/claim=  150,796 cached= 80% $/claim=0.2196 errors=0
     R1   Trim the TBOM                            claims= 50 accuracy=100.0% tokens/claim=   59,091 cached= 57% $/claim=0.1363 errors=0
     R2   Tier the models                          claims= 50 accuracy=100.0% tokens/claim=   59,363 cached= 49% $/claim=0.0600 errors=0
     R3   Cache the prefix                         claims= 50 accuracy=100.0% tokens/claim=   59,703 cached= 97% $/claim=0.0233 errors=0
     R5   Production: R3 + guards                  claims= 50 accuracy=100.0% tokens/claim=   59,319 cached= 97% $/claim=0.0233 errors=0
     List-price estimate for this invocation: $12.15.

     run_tag=blog-1015  claims=40  runs=['R4U', 'R4G']  ->  .../results/blog-1015
     R4U  Flaky dependency, no guards              claims= 40 accuracy= 87.5% tokens/claim=  101,170 cached= 95% $/claim=0.0363 errors=4
     R4G  Flaky dependency, loop guards            claims= 40 accuracy=100.0% tokens/claim=   62,048 cached= 97% $/claim=0.0253 errors=0
     ```
- **🖼️ What to frame:** The clean terminal output showing all 7 run summary lines (`R0, R1, R2, R3, R5` and `R4U, R4G`).
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The `accuracy=100.0%` column across `R0 → R5`, proving quality never dropped as cost fell.
  2. Box 2: The `$/claim` drop from **`0.2196` (`R0`)** down to **`0.0233` (`R5`)** (**-89%**).
  3. Box 3: The `R4U` vs `R4G` comparison (`accuracy=87.5% $/claim=0.0363 errors=4` vs. `accuracy=100.0% $/claim=0.0253 errors=0`).
- **🔒 What to redact:** Local home directory path if shown.

---

### Step 5 — Token-Burn Alert Firing During the `R4U` Failure Scenario (`E5`) → `images/s11_alert.png`

- **🎯 What this proves in the blog:** When we injected a 20% upstream timeout into `screen_fraud` in `R4U` (without loop guards), the 15-call retry loops spiked project-wide token consumption from `R5`'s healthy peak of **645,546 tokens/min** up to **905,391 tokens/min**—breaching our **750,000 tokens/min** threshold for 4 consecutive minutes (`09:52–09:55 UTC` / `15:22–15:25 IST`) and firing an alert to `rajdipch@google.com`. Then, when `R4G` ran with `max_same_call=2` (`09:57–10:01 UTC`), token burn stayed below the threshold (**726,753 tokens/min** peak).
- **🧭 Step-by-step Console clicks:**
  1. Open [Cloud Monitoring → Alerting → Policies](https://console.cloud.google.com/monitoring/alerting/policies/8458942289128046040?project=<YOUR_PROJECT_ID>) and click **`TBOM demo - Gemini token burn rate`**.
  2. In the time-range picker at the top right of the condition chart, click **Custom** and set:
     - **Start:** `15 Oct 2026, 09:45 UTC` (`15:15 IST`)
     - **End:** `15 Oct 2026, 10:02 UTC` (`15:32 IST`)
  3. Look at the condition chart (and any listed Incident / your `rajdipch@google.com` inbox):
     - `09:45–09:50 UTC` (`R5`): curve sits around `591K–646K` tokens/min (below the dashed `750K` threshold line).
     - `09:52–09:55 UTC` (`R4U`): curve crosses above the `750K` dashed line (`753K → 801K → 823K → 905K` tokens/min).
     - `09:57–10:01 UTC` (`R4G`): curve drops back below the `750K` dashed line (`727K` peak, then `681K → 473K`).
- **🖼️ What to frame:** The Alert Policy page showing the condition chart over `09:45–10:02 UTC` (`15:15–15:32 IST`), the dashed threshold line at `750,000`, and the Incidents / Notifications section below it. (Optional bonus: inset or side-by-side crop of the alert email received in `rajdipch@google.com`!)
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Callout 1 (`09:45–09:50 UTC`): Label **`R5 (Healthy): 645.5K tok/min peak (below threshold)`**.
  2. Callout 2 (`09:52–09:55 UTC`): Circle the spike above the red threshold line and label **`R4U (Unguarded failure loop): 905.4K tok/min peak — ALERT FIRED`**.
  3. Callout 3 (`09:57–10:01 UTC`): Label **`R4G (With loop guards): 726.8K tok/min peak (below threshold)`**.
- **🔒 What to redact:** Project ID `<YOUR_PROJECT_ID>`.

---

### Step 6 — One Claim in Cloud Trace (`E6`) → `images/s03_trace.png`

- **🎯 What this proves in the blog:** Every claim produces an OpenTelemetry trace tree (`claim` root span → `gen_ai.triage` on Flash-Lite → `gen_ai.adjudicate` spans on 3.8 Flash), with exact `gen_ai.usage.*` token counts, cached tokens, and `tbom.cost_usd` attached to each span.
- **🧭 Step-by-step Console clicks:**
  1. Open [Cloud Trace → Trace explorer](https://console.cloud.google.com/traces/explorer?project=<YOUR_PROJECT_ID>).
  2. Set the time-range picker (top right) to cover **`15 Oct 2026, 09:45 UTC – 10:02 UTC`** (`15:15 IST – 15:32 IST`).
  3. Paste one of these verified Trace IDs directly into the **Trace ID** lookup box:
     - **Healthy `R5` claim trace ID:** `00c69fdd580477c6083d451084815b13` (or `0359cc6efa977fc15208b51b09a348ad`)
     - *(Optional comparison)* **Looping `R4U` claim trace ID:** `010a21c6cec39a4da2f43f58b1c57466`
  4. In the waterfall waterfall view on the left, click one of the **`gen_ai.adjudicate`** child spans so the **Attributes** tab opens on the right.
- **🖼️ What to frame:** Both the span waterfall tree on the left (showing 1 `gen_ai.triage` span + 3 `gen_ai.adjudicate` spans under `claim`) and the **Attributes** panel on the right.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1 (Left panel): The **`claim` → `gen_ai.triage` + `gen_ai.adjudicate`** span hierarchy.
  2. Box 2 (Right panel — Attributes):
     - `gen_ai.request.model`: `gemini-3.8-flash`
     - `gen_ai.usage.input_tokens`: `~19,100`
     - `tbom.cached_tokens`: `18,643` (showing 97% of the prompt came from the explicit context cache!)
     - `tbom.cost_usd`: `~0.005–0.009`
- **🔒 What to redact:** `gcp.project_id` in the Attributes tab and `<YOUR_PROJECT_ID>` in the top bar.

---

### Step 7 — Gemini Platform Model Observability Dashboard (`E7`) → `images/s04_model_observability.png`

- **🎯 What this proves in the blog:** Out-of-the-box Model Observability on Gemini Platform (formerly Vertex AI) tracks request throughput, token volume, and error rates per GA model (`gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`) without custom instrumentation.
- **🧭 Step-by-step Console clicks:**
  1. Open [Agent Platform (Gemini Platform) → Dashboard](https://console.cloud.google.com/vertex-ai/dashboard?project=<YOUR_PROJECT_ID>).
  2. In the **Model observability** section, click **Show all metrics** (or select all 3 models: `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`).
  3. Set the time window to **`15 Oct 2026, 08:05 UTC – 10:05 UTC`** (`13:35 IST – 15:35 IST`) so both the `R0` Argon baseline and the `R1–R5` tiered Flash/Flash-Lite runs appear.
- **🖼️ What to frame:** The Model Observability charts showing **Token count / Throughput** and **Request count / Latency** split by model name.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The model legend showing all three GA models (`gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`).
  2. Box 2: The handover from `gemini-4-argon` (in `R0` and `R1`) to `gemini-3.5-flash-lite` + `gemini-3.8-flash` (in `R2–R5`).
- **🔒 What to redact:** Project ID `<YOUR_PROJECT_ID>`.

---

### Step 8 — Loading Results into BigQuery via Console Upload (`E8`) → `images/c06_upload_table.png`

- **🎯 What this proves in the blog:** Readers don't need an ETL pipeline to analyze their agent's TBOM—they can upload `calls.jsonl` directly in the BigQuery Console using `sql/schemas/calls.json`.
- **🧭 Step-by-step Console clicks:** *(Note: The real tables `calls`, `claims`, and `runs` are already loaded in `<YOUR_PROJECT_ID>:tokenomics_demo`. Open the form for the screenshot, then click **Cancel**.)*
  1. Open [BigQuery Studio](https://console.cloud.google.com/bigquery?project=<YOUR_PROJECT_ID>).
  2. In the **Explorer** pane, expand your project → click `⋮` next to **`tokenomics_demo`** → click **Create table**.
  3. Fill in the dialog:
     - **Create table from:** `Upload`
     - **Select file:** browse to `results/blog-1015/calls.jsonl`
     - **File format:** `JSONL (Newline delimited JSON)`
     - **Table:** `calls`
     - **Schema:** toggle **Edit as text** ON and paste the contents of `sql/schemas/calls.json`.
- **🖼️ What to frame:** The **Create table** side panel showing `Upload`, `JSONL`, table name `calls`, and the JSON schema pasted into the **Edit as text** box. (Click **Cancel** after taking the screenshot.)
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: **Create table from: `Upload`** and **File format: `JSONL`**.
  2. Box 2: The **Schema → Edit as text** box showing the TBOM fields (`system_prompt_tokens`, `handbook_tokens`, `tool_schema_tokens`, `history_tokens`, `thinking_tokens`, `cost_usd`).
- **🔒 What to redact:** Project ID `<YOUR_PROJECT_ID>` in the Destination section.

---

### Steps 9–13 — BigQuery Studio Charts (`E9`–`E13`)

For each of the five BigQuery charts below:
1. Open [BigQuery Studio](https://console.cloud.google.com/bigquery?project=<YOUR_PROJECT_ID>) and click **`+` (SQL query)**.
2. Paste the SQL query shown for that step and click **Run**.
3. In the **Query results** pane at the bottom, click the **Visualization** tab (next to *Results* and *JSON*) and configure the chart type and fields listed below.

---

#### Step 9 — The Cost Waterfall (`E9`) → `images/s05_bq_waterfall.png`

- **🎯 What this proves in the blog:** Across the same 50 claims, cost per claim dropped **89%** from **`$0.2196` (`R0`)** → **`$0.1363` (`R1`)** → **`$0.0600` (`R2`)** → **`$0.0233` (`R3`)** → **`$0.0233` (`R5`)**, while accuracy remained **100.0% (`50/50`)** in every run.
- **SQL to run:**
  ```sql
  SELECT run_label, cost_per_claim_usd, ROUND(accuracy * 100, 1) AS accuracy_pct, tokens_per_claim
  FROM tokenomics_demo.v_run_summary
  WHERE run_tag = 'blog-1015' AND run_id IN ('R0','R1','R2','R3','R5')
  ORDER BY run_order;
  ```
- **Visualization settings:** Chart type = **Bar / Column chart** · Dimension (X-axis) = `run_label` · Measure (Y-axis) = `cost_per_claim_usd`.
- **🖼️ What to frame:** The query editor at the top and the **Visualization** bar chart (plus the 5-row result table if visible).
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The `R0` bar (**`$0.2196`**) vs. the `R5` bar (**`$0.0233`**), with an arrow labeled **`-89% cost per claim at 100% accuracy`**.

---

#### Step 10 — The Token Bill of Materials, `R0` vs. `R5` (`E10`) → `images/s06_bq_tbom.png`

- **🎯 What this proves in the blog:** `R0`'s bill was dominated by **re-read conversation history (`48%` of tokens)** and the **handbook (`42%`)**, whereas the claim itself was **`0.3%`**. In `R5`, multi-turn history waste is eliminated and the handbook is served 97% from cache.
- **SQL to run:**
  ```sql
  SELECT run_id, line_item, ROUND(usd_per_claim, 4) AS usd_per_claim, ROUND(tokens_per_claim, 0) AS tokens_per_claim
  FROM tokenomics_demo.v_tbom_by_run
  WHERE run_tag = 'blog-1015' AND run_id IN ('R0','R1','R2','R3','R5')
  ORDER BY run_id, line_item;
  ```
- **Visualization settings:** Chart type = **Stacked bar / Stacked column** · Dimension (X-axis) = `run_id` · Breakdown / Series = `line_item` · Measure (Y-axis) = `usd_per_claim` (or `tokens_per_claim`).
- **🖼️ What to frame:** The stacked bar chart comparing the 8 TBOM line items across `R0`, `R1`, `R2`, `R3`, and `R5`.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The massive **`history`** and **`handbook`** segments in `R0` that disappear or shrink by ~90% in `R1–R5`.
  2. Box 2: The **`thinking`** segment (which is billed at output token rates and becomes the main non-cached cost driver once the prompt is cached).

---

#### Step 11 — Median (`p50`) vs. 95th Percentile (`p95`) Token Variance (`E11`) → `images/s07_bq_variance.png`

- **🎯 What this proves in the blog:** Why FinOps budgets must be built on the tail (`p95`), not the mean: in `R0`, `p95` (`231,640` tokens) was **`1.6×`** the median (`149,278`). In `R5`, the tail tightened to **`1.0×`** (`59,300` median vs. `60,027` p95). When `R4U` hit the unguarded failure loop, `p95` exploded to **`279,368` tokens (`4.7×` median)**, whereas `R4G`'s loop guard kept `p95` at **`78,832` (`1.3×` median)**.
- **SQL to run:**
  ```sql
  SELECT run_id, p50_tokens, p95_tokens, p95_to_p50_ratio
  FROM tokenomics_demo.v_token_variance
  WHERE run_tag = 'blog-1015'
  ORDER BY run_id;
  ```
- **Visualization settings:** Chart type = **Grouped bar / Column chart** · Dimension = `run_id` · Measures = `p50_tokens` and `p95_tokens`.
- **🖼️ What to frame:** The grouped bar chart showing `p50_tokens` and `p95_tokens` side by side for every run (`R0, R1, R2, R3, R4U, R4G, R5`).
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: **`R5`** (`p50 = 59,300`, `p95 = 60,027`, ratio `1.01×` — predictable tail).
  2. Box 2: **`R4U` vs. `R4G`** (`R4U` p95 spikes to `279,368` tokens [`4.67×`], while `R4G` caps p95 at `78,832` [`1.32×`]).

---

#### Step 12 — Same Tokens, Different Consumption Lanes (`E12`) → `images/s09_bq_lanes.png`

- **🎯 What this proves in the blog:** Re-pricing the exact measured tokens across `Standard PayGo`, `Priority PayGo`, `Flex PayGo`, and `Batch` shows two key insights: (1) `Flex` doesn't help `R0` (`$0.220` unchanged) because Gemini 4 Argon does not offer Flex PayGo (`lane_fully_available = FALSE`), and (2) moving `R5` (`$0.023`) to `Flex` or `Batch` cuts token cost in half again to **`$0.011/claim`** for latency-tolerant back-office work.
- **SQL to run:**
  ```sql
  SELECT run_id, lane, usd_per_claim, change_vs_standard, lane_fully_available
  FROM tokenomics_demo.v_lane_projection
  WHERE run_tag = 'blog-1015' AND run_id IN ('R0','R5')
  ORDER BY run_id, lane;
  ```
- **Visualization settings:** Chart type = **Grouped bar chart** · Dimension = `run_id` · Series = `lane` · Measure = `usd_per_claim`.
- **🖼️ What to frame:** The grouped bar chart (or query results table) comparing `R0` and `R5` across `batch`, `flex`, `priority`, and `standard`.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: `R0` `flex` = `$0.2196` (`lane_fully_available = false` because Argon has no Flex tier).
  2. Box 2: `R5` `flex` / `batch` = **`$0.0114/claim`** (`-50%` vs. Standard).

---

#### Step 13 — Cost per Correctly Resolved Claim (`CpO`, `E13`) → `images/s08_bq_cpo.png`

- **🎯 What this proves in the blog:** Total **Cost per Outcome (`CpO`)** came down from **`$2.86` per correct claim in `R0`** to **`$2.66` in `R5`** at **100% accuracy (`rework_usd_per_correct = $0.00`)**. Once tokens are optimized down to `$0.023/claim` (**`0.9%`** of `R5`'s CpO), **99.1% of the remaining `$2.66` cost (`$2.64/claim`) is human review** of the 11 escalated claims. And in `R4U`, the unguarded failure loop pushed `CpO` up to **`$6.04/claim`** due to `$2.57/claim` in rework on failed claims, whereas `R4G`'s loop guards brought `CpO` down to **`$4.23/claim`** with `$0.00` rework!
- **SQL to run:**
  ```sql
  SELECT run_id, llm_usd_per_correct, tools_usd_per_correct, review_usd_per_correct, rework_usd_per_correct, cpo_usd, ROUND(llm_share_of_cpo * 100, 1) AS llm_pct
  FROM tokenomics_demo.v_cpo_by_run
  WHERE run_tag = 'blog-1015'
  ORDER BY run_id;
  ```
- **Visualization settings:** Chart type = **Stacked bar chart** · Dimension = `run_id` · Measures = `llm_usd_per_correct`, `tools_usd_per_correct`, `review_usd_per_correct`, `rework_usd_per_correct`.
- **🖼️ What to frame:** Both the stacked bar chart and the 7-row results table underneath it so readers can see the exact `cpo_usd` and `llm_pct` numbers.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: **`R0` (`cpo_usd = $2.86`, `llm_pct = 7.7%`) → `R5` (`cpo_usd = $2.66`, `llm_pct = 0.9%`)** with `$0.00` rework across `R0–R5`.
  2. Box 2: **`review_usd_per_correct = $2.64`** (showing human review of escalations is now 99% of the outcome cost).
  3. Box 3: **`R4U` (`cpo_usd = $6.04` with `$2.57` rework) vs. `R4G` (`cpo_usd = $4.23` with `$0.00` rework)**.

---

### Step 14 — The Real Invoice by Request Label (`E15`) → `images/s13_billing_labels.png`

- **🎯 What this proves in the blog:** Request labels (`app=cymbal-claims`, `experiment=tbom`, `run=r0..r5`, `step=triage|adjudicate`, `tier=frontier|flash|flash-lite`) flow into the BigQuery Cloud Billing export, showing gross cost, promotional 50% credits, net cost, and unlabelled cache-storage SKUs.
- **🧭 Step-by-step Console clicks:**
  1. Wait a few hours after enabling Cloud Billing export (Step 3) for the `billing_export.gcp_billing_export_resource_v1_XXXXXX` table to populate.
  2. Open `sql/07_billing_by_label.sql` in BigQuery Studio, replace `billing_export.gcp_billing_export_resource_v1_XXXXXX_XXXXXX_XXXXXX` with your actual export table name, and click **Run**. Then run `sql/08_estimate_vs_invoice.sql`.
  3. Run:
     ```sql
     SELECT run_id, step, tier, sku, gross_cost, credits, net_cost
     FROM tokenomics_demo.v_billing_by_label
     WHERE run_tag = 'blog-1015'
     ORDER BY run_id, net_cost DESC;
     ```
- **🖼️ What to frame:** The BigQuery results grid showing `run_id`, `step`, `tier`, `sku`, `gross_cost`, `credits`, and `net_cost`.
- **🖍️ What to highlight (draw a red box/arrow around):**
  1. Box 1: The `run_id`, `step`, and `tier` columns populated directly from Gemini API `labels`.
  2. Box 2: The `gross_cost` vs. `credits` vs. `net_cost` columns (showing the promotional credit offset).
- **🔒 What to redact:** Billing Account ID in the table name if visible in the SQL editor.

---

### Steps 15 & 16 *(Optional)* — Apigee AI Gateway (`E16` & `E17`) → `images/c09_apigee_policies.png` & `images/s14_apigee_analytics.png`

*(Only capture these if you choose to deploy the optional Apigee gateway in RUNBOOK Step 11. The blog explicitly notes that Apigee is architectural and not part of the default Cloud Shell script run.)*

- **`E16` (`images/c09_apigee_policies.png`):**
  - **Where:** Console → **Apigee → Proxy development → API proxies → your Gemini proxy → Develop** tab.
  - **What to highlight:** The **`LLMTokenQuota`** policy and **`PromptTokenLimit`** policy attached to the proxy Request PreFlow.
- **`E17` (`images/s14_apigee_analytics.png`):**
  - **Where:** Console → **Apigee → Analytics → API metrics** (filtered to your proxy).
  - **What to highlight:** Traffic grouped by Developer App and the **`429 Too Many Requests`** spike once `LLMTokenQuota` is exhausted.

---

### Bonus — Live Deployed Google ADK Agent on Cloud Run & Gemini Platform Agent Runtime

Both deployment targets (`deploy/03_deploy_cloud_run.sh` and `deploy/04_deploy_agent_runtime.py`) are live in `<YOUR_PROJECT_ID>`:

1. **Cloud Run (`cymbal-claims-tbom-agent` in `us-central1`):**
   - **Console URL:** [Cloud Run → cymbal-claims-tbom-agent](https://console.cloud.google.com/run/detail/us-central1/cymbal-claims-tbom-agent/metrics?project=<YOUR_PROJECT_ID>)
   - **Service Endpoint:** `https://cymbal-claims-tbom-agent-gube7zconq-uc.a.run.app`
   - **Smoke Test Command:**
     ```bash
     python deploy/05_test_deployed_agent.py \
       --cloud-run-url https://cymbal-claims-tbom-agent-gube7zconq-uc.a.run.app \
       --claim-ref CLM-000001
     ```
2. **Gemini Platform Agent Runtime (`cymbal-claims-tbom-agent` in `us-central1`):**
   - **Resource Name:** `projects/<YOUR_PROJECT_NUMBER>/locations/us-central1/reasoningEngines/6406608239324037120`
   - **Smoke Test Command:**
     ```bash
     python deploy/05_test_deployed_agent.py \
       --agent-runtime-id projects/<YOUR_PROJECT_NUMBER>/locations/us-central1/reasoningEngines/6406608239324037120 \
       --claim-ref CLM-000001
     ```

---

## 🖼️ Pre-Rendered Diagrams & Tables (`medium_assets/` — Already Generated for You!)

All **11** diagrams and tables that Medium cannot render natively have already been generated from the live `blog-1015` data at 2× retina resolution in `medium_assets/`:

| File | What It Shows |
| :--- | :--- |
| `medium_assets/table_1_four_meters.png` | The four meters on an AI bill (Token, Resource, Provisioned, Seat) |
| `medium_assets/table_1b_extensions.png` | **NEW:** Layer 4 Harness Extensions (`SKILL.md`, `AGENTS.md`, Commands & Hooks, Plugins, MCP) token footprint comparison |
| `medium_assets/diagram_1_apigee_gateway.png` | Apigee AI Gateway architecture (`LLMTokenQuota`, `PromptTokenLimit`, Semantic Cache, routing, chargeback) |
| `medium_assets/table_2_vanity_vs_outcome.png` | Vanity metrics vs. business outcomes worth measuring |
| `medium_assets/table_3_data.png` | Synthetic Cymbal Insurance dataset summary (8k customers, 12k policies, 60k history, 5k claims) |
| `medium_assets/diagram_2_architecture.png` | End-to-end experiment architecture (Cloud Shell → Gemini Platform → Trace, Monitoring, Billing, BigQuery) |
| `medium_assets/table_4_models_prices.png` | The three GA models (`Gemini 4 Argon`, `Gemini 3.8 Flash`, `Gemini 3.5 Flash-Lite`) and list prices |
| `medium_assets/table_5_scoreboard.png` | **Updated:** Measured scoreboard (`R0 → R5`: **89% lower token cost**, **100% accuracy across all 5 designs**, **CpO `$2.86 → $2.66`**) |
| `medium_assets/table_6_consumption_options.png` | Gemini Platform consumption options (`Standard`, `Flex`, `Priority`, `Batch`, `Off-peak/Deferred`, `PT + FSP`) |
| `medium_assets/table_7_pt_what_if.png` | Provisioned Throughput sizing what-if (`p30` to `p90` utilization vs. spillover) |
| `medium_assets/diagram_3_lane_decision_tree.png` | Decision tree for choosing a Gemini consumption option |

# AI + AI Backend PRD — Restaurant CRM Platform

This PRD defines the AI features and the AI backend service for the Restaurant CRM Platform. It extracts and focuses the AI-related scope from the master PRD and specifies functional requirements, data flows, models, APIs, and delivery milestones required to ship the AI capabilities.

## 1) Objectives & Success Metrics
- Improve profitability through AI recommendations and data-driven decisions (source: master PRD).
- Provide AI-driven insights and analytics to stakeholders across departments (source: master PRD).
- Reduce waste and stock discrepancies via AI-driven optimization.
- Accelerate planning with accurate forecasts for demand and inventory.

Success metrics (initial targets; refine during discovery):
- Forecast accuracy: MAPE ≤ 20% at item/day; coverage ≥ 90% of top-selling SKUs.
- Inventory: ≥ 30% reduction in stock-outs; ≥ 15% reduction in overstock days.
- Yield: ≥ 10–15% reduction in prep waste; yield variance ≤ 5%.
- Pricing/menu: ≥ 3–5% gross profit lift on optimized items (guard-railed).
- Latency: ≤ 1s p95 for on-demand yield/insight endpoints; ≤ 5s p95 for small-ROI pricing recs; async for heavy jobs.

## 2) In Scope
- Demand forecasting: Predict near-term sales at item × location × time bucket.
- Inventory optimization: Reorder points, safety stock, and purchase suggestions using forecasts, lead times, and costs.
- Recipe yield calculation (AI-powered): Compute precise ingredient quantities for desired outputs; adjust for shrinkage and seasonal/price constraints.
- Menu pricing & mix optimization: Price recommendations and menu mix suggestions using elasticity and profitability constraints.
- AI insights & dashboard: Surface actionable, explainable recommendations for Super Admin and department dashboards.

Out of scope (initial phases):
- CV/IoT features, computer vision, autonomous robots.
- Conversational agents/LLMs and NLP chat assistants.
- Fully autonomous price changes (only suggestions in early phases).

## 3) Users & Core Workflows
Personas (from master PRD):
- Super Admin (Owner/Manager): Views AI insights, sets AI thresholds, approves actions.
- Procurement: Receives reorder suggestions; plans purchase orders using AI.
- Processing: Uses AI yield calculator for recipe prep; updates recipes per AI guidance.
- Kitchen: Uses predicted yields, receives optimization tips to reduce waste.
- Finance: Reviews AI-recommended pricing/menu optimization and margin impacts.

Key workflows:
- AI Analytics Access (Super Admin): Access and configure AI insights; view demand forecasts; apply menu and pricing recommendations.
- Recipe Management & AI Integration (Processing): Input desired outputs → AI computes raw material quantities and yields.
- AI-Powered Yield Calculation (Processing/Kitchen): Predict output quantities and optimize ingredient usage; adjust for seasonal cost/availability.
- Procurement Optimization (Procurement): Review reorder points and purchase suggestions aligned to forecast and lead times.
- Pricing/Menu Optimization (Finance/Super Admin): Review recommended price ranges and menu mix shifts with expected GP/NPM impact.

## 4) Data Sources
- Sales/transactions: item_id, location_id, timestamp, qty, net price, discount, tax.
- Inventory levels & movements: item_id, location_id, on_hand, committed, received, issued, expiry.
- Recipes/BOM & yield factors: recipe_id, ingredient_id, base_qty, yield/shrinkage %, prep loss factors.
- Procurement & supplier costs: supplier_id, item_id, last_cost, lead_time_days, MOQ, contract terms.
- Waste/spoilage & returns: item_id, qty_waste, reason_code, timestamp.
- Calendars & events: holidays, promotions, seasonality tags.

Minimum freshness for online inference:
- Sales ≤ 15 min lag; inventory ≤ 15 min; costs weekly or upon change; recipes on update.

## 5) Models & Methods
- Demand forecasting
  - Problem: Item × location short-horizon forecasting (e.g., 1–14 days, optional intra-day).
  - Methods: Hierarchical/grouped time series (SARIMAX/Prophet), gradient boosting with calendar/promotions, or hybrid. Cold-start fallback by category/location analogs.
  - Outputs: Point forecast, prediction intervals; feature importances/explanations where applicable.
- Inventory optimization
  - Compute reorder point (ROP) and safety stock using forecast error, desired service level, lead time variability, and demand variance.
  - Outputs: Suggested order qty (EOQ or cost-aware batch), reorder date, supplier suggestion and rationale.
- Recipe yield calculation (AI-powered)
  - Deterministic stoichiometry from BOM with learned yield/shrinkage factors. Optional regression to calibrate yields from historical prep vs. output.
  - Outputs: Ingredient list with quantities, expected yield, waste projection, and sensitivity to constraints (cost, availability).
- Pricing & menu optimization
  - Price elasticity estimation (econometric or ML), contribution margin maximization with guardrails (price bounds, min GP). Menu mix categorization using sales/GP and constraints. Bandit/A-B framework for safe rollout.
  - Outputs: Price recommendations with expected GP lift and risk bounds; menu mix suggestions.
- Menu optimization & BCG classification
  - Classify items by profitability and popularity (e.g., BCG: Star, Cash Cow, Question Mark, Dog) using sales volume, margin, and stability; propose mix adjustments under constraints.
  - Outputs: Item categories, recommended menu mix changes, candidate additions/removals, expected impact.
- Waste prediction & prevention
  - Predict near-term waste risk from inventory position, expiries, and demand; detect anomalies and probable root causes.
  - Outputs: Waste risk scores, preventive actions (prep timing, transfers, substitution), and expected financial impact.
- Anomaly/waste monitoring
  - Lightweight anomaly detection on waste, prep yield variance, and sudden sales dips/spikes.

Evaluation metrics (per model):
- Forecast: MAPE, sMAPE, MAE; coverage for PI; WAPE per top SKUs.
- Inventory: Stock-out rate, overstock days, realized service level.
- Yield: Mean absolute yield error; waste % vs baseline.
- Pricing: Realized GP lift vs control; elasticity sanity constraints.

## 6) Training, Data, and MLOps
- Training cadence: Nightly retrains for forecasts and yield factors; weekly pricing model refresh; on-demand backfills for new stores/SKUs.
- Feature computation: Batch pipelines build aggregate features (lags, moving averages, seasonality, calendar). Maintain an offline store (warehouse tables) and a minimal online cache for hot features.
- Model registry & versioning: Track models, metadata, metrics; include canary/stable tags; store artifacts in object storage.
- Rollouts: Shadow and canary evaluation before promote; guardrails and kill-switch via config.
- Feedback: Explicit approval/feedback events (accept/reject recommendations) captured to improve models.

## 7) AI Backend Architecture
- Service: `ai-service` (separate microservice).
  - Public REST API for low-latency inference and insights.
  - Async workers/queue for heavy jobs (e.g., batch optimization, backfills).
- Storage
  - Primary OLTP (reads): Postgres/primary DB replicas (read-only for AI service).
  - Warehouse/Lake: For training and batch features (e.g., BigQuery/Snowflake/Postgres warehouse). Exact choice aligned with platform.
  - Object storage: Model artifacts and large outputs.
  - Cache: Redis for feature caching and async job coordination.
- Messaging/Jobs
  - Queue (e.g., Redis+RQ/Celery) for retraining, long-running optimizations, and scheduled tasks.
  - Scheduler (cron/worker) for nightly/weekly training jobs.
- Real-time delivery
  - Optional WebSocket `/ws/updates` or Server-Sent Events `/updates/stream` for live insights to dashboards (alerts, recommendations, predictions). Default fallback is pull via REST.
  - Event payload: `{ type: 'prediction'|'alert'|'recommendation', department, priority, payload: { message, data, actionRequired } }`.
- Security & Access
  - Service-to-service auth (JWT/mTLS), RBAC by role (Super Admin, Procurement, Processing, Kitchen, Finance).
  - PII minimization; encryption in transit and at rest; audit logs.

## 8) API Design (initial)
Base: `/api/ai/v1`

Standard request/response schema (envelope):
- Request: `{ request_id, timestamp, org_id, user_id?, context? }`
- Response: `{ request_id, status: 'ok'|'processing'|'error', data?, predictions?, recommendations?, model_version?, generated_at?, error? }`

Endpoints:
- GET `/forecast`
  - Query: `item_id`, `location_id`, `horizon_days` (1–14), `bucket` (day|hour), `confidence` (e.g., 0.8)
  - Response: `{ forecasts: [{ ts, qty, lower, upper }], model_version, generated_at }`
- POST `/yield/calc`
  - Body: `{ recipe_id, desired_output_qty, constraints?: { max_cost?, exclude_ingredients?: [id], substitutions?: [{ from, to }] } }`
  - Response: `{ ingredients: [{ id, qty, unit }], expected_yield, waste_pct, notes?, model_version }`
- GET `/inventory/reorder-suggestions`
  - Query: `location_id`, optional filters (`supplier_id`, `category`, `days_ahead`)
  - Response: `{ suggestions: [{ item_id, reorder_point, suggested_qty, supplier_id?, lead_time_days?, rationale }], generated_at }`
- POST `/pricing/recommendations`
  - Body: `{ items: [{ item_id, current_price }], constraints?: { min_margin_pct?, price_bounds?: [{ item_id, min, max }] } }`
  - Response: `{ recommendations: [{ item_id, suggested_price, expected_gp_lift_pct, confidence }], experiment?: { id, variant } }`
- GET `/menu/bcg-classification`
  - Query: `location_id`, optional: `category`, `period`
  - Response: `{ items: [{ item_id, class: 'star'|'cash_cow'|'question_mark'|'dog', profitability_pct, popularity_percentile }], rationale?, generated_at }`
- POST `/menu/optimize`
  - Body: `{ constraints?: { menu_size?, min_margin_pct?, exclude_items?: [id] }, objectives?: { profit_weight?, popularity_weight? } }`
  - Response: `{ actions: [{ type: 'promote'|'demote'|'remove'|'add', item_id?, details }], expected_impact: { gp_lift_pct?, sales_lift_pct? } }`
- POST `/waste/predict`
  - Body: `{ location_id, horizon_days?: 7 }`
  - Response: `{ risks: [{ item_id, risk_score, drivers: [string], expiry_date?, expected_loss_value }], generated_at }`
- GET `/waste/analysis`
  - Query: `location_id`, `date_range`
  - Response: `{ summary: { total_waste_value, top_causes: [string] }, items: [{ item_id, waste_qty, waste_value, causes: [string] }], recommendations: [string] }`
- GET `/insights`
  - Query: `role` (admin|procurement|processing|kitchen|finance), `location_id`
  - Response: Curated insights feed with explanations and actions.
- POST `/feedback`
  - Body: `{ type: 'accept'|'reject'|'adjust', entity: 'pricing'|'inventory'|'yield'|'forecast'|'waste'|'menu', id?, details? }`
  - Response: `{ ok: true }`
- Real-time updates
  - SSE: GET `/updates/stream` (events: `prediction`, `alert`, `recommendation`).
  - WebSocket: `/ws/updates` for bi-directional notifications.
  - Event sample: `{ type, department, priority, payload: { message, data, actionRequired } }`.

Auth & rate limits: Service tokens + user JWT; rate limits per org and per endpoint. Heavy endpoints return `202 Accepted` with job id; results fetched via `/jobs/{id}`.

## 9) Non‑Functional Requirements
- Availability: ≥ 99.9% during operating hours.
- Latency: p95 under targets in Section 1; async for heavy jobs.
- Scalability: Horizontal workers; cache hot paths; idempotent jobs.
- Cost: Prefer cost-aware models; batch when feasible; archive old artifacts.
- Privacy: No PII in models; strict access controls; audit trails.

## 10) Monitoring & Quality
- Service: p50/p95 latency, error rates, queue lengths, job success/failure.
- Data: Freshness SLAs; missing data alerts; schema drift checks.
- Model: Forecast error dashboards; yield error trends; pricing outcome lift; drift detectors; canary vs stable comparison.
- Alerting: On-call rotation with severity thresholds; auto rollback to last-good model.

## 11) Dependencies & Assumptions
- Upstream dependencies from master PRD:
  - Database schema completion before API development.
  - Authentication in place before role-based features.
  - Core API services before full frontend integration.
  - Real-time infrastructure before notifications.
  - AI model training before analytics implementation.
- Data availability: Sales, inventory, recipes, costs, and events accessible via read replicas/warehouse.
- Org/Role metadata available for RBAC and scoping.

## 12) Delivery Plan (Phased)
- Phase 0 — Data readiness (Weeks 1–3)
  - Read models/tables stable; ingestion jobs; feature definitions; observability baseline.
- Phase 1 — MVP Yield & Insights (Weeks 4–6)
  - `/yield/calc`, basic insights; initial dashboards for Super Admin/Processing; feedback capture.
- Phase 2 — Forecast + Inventory (Weeks 7–12)
  - `/forecast`, `/inventory/reorder-suggestions`; procurement workflow hooks; accuracy dashboards; canary rollouts.
- Phase 3 — Pricing/Menu (Weeks 13–18)
  - `/pricing/recommendations` with guardrails; experiment hooks; finance-facing views.
- Phase 4 — Hardening & Scale (Weeks 19–20)
  - Performance tuning, caching, backpressure; security hardening; SLOs.
- Phase 5 — Observability & Autonomy (Weeks 21–22)
  - Advanced monitoring, drift/rollback, automation of safe approvals where allowed.

## 13) Risks & Mitigations
- Sparse or noisy data → Use hierarchical pooling, smoothing, and category rollups.
- Cold start for new items/locations → Category/location analogs and Bayesian priors.
- Model drift due to promos/seasonality → Frequent retrains; promo features; drift detection.
- Over-automation risk → Human-in-the-loop approvals; clear explanations; guardrails.
- Latency spikes → Async processing; caching; precompute top insights nightly.

## 14) Open Questions
- Final choice of warehouse/lake and job runner within platform standards?
- Exact RBAC mapping per endpoint? Any cross-org multi-tenant constraints?
- Promotion/promo data source availability and structure?
- Required granularity for forecast (hour vs day) for each store type?
- Pricing guardrails: acceptable price ranges and compliance constraints?

## 15) Source Alignment (from master PRD)
- Executive Summary: “Improve profitability through AI recommendations and data-driven decisions.”
- Goals: “Provide AI-driven insights.”
- Super Admin: “AI Analytics Access” — demand forecasting, inventory optimization, pricing/menu optimization.
- Processing: “Recipe Management & AI Integration” — optimal raw material quantities.
- Processing: “AI-Powered Yield Calculation” — precise ingredient quantities, predict outputs, minimize waste.
- Dependencies: “AI model training before analytics implementation.”
- Team: “AI/ML Engineer” responsibilities including predictive models and recommendation system.
- Roadmap: “Advanced AI Features: Enhanced predictive analytics and recommendation engines; ML-driven autonomous operations.”

---

Owner: AI/ML Engineering + Backend Team
Version: v0.1 (Initial Draft)
Last Updated: <auto>

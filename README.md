## Deploy-Confidence-Service
![deploy-confidence-architecture](img/deploy-confidence-architecture2.png)

A Kubernetes-native decision service that converts platform signals into a deployment confidence score and exposes the result through API, PostgreSQL-backed history, Grafana dashboards, and CI/CD deployment gates.

### The problem it solves

In many environments, deployment safety is still judged manually.

Teams look at:
- cluster health
- recent restarts
- image pull failures
- startup latency
- dependency reachability
- dashboards and alerts

and then make a human judgment:

**“Does this platform look safe enough to deploy right now?”**

That sounds simple, but in practice it is inconsistent.

> Different engineers interpret the same signals differently. Dashboards may look healthy at a glance while rollout-critical paths are degraded underneath. A cluster can be technically “up” while still being a poor deployment target because image pulls are failing, startup latency is drifting, or dependency paths are unstable.

This project was built to solve that gap.

Instead of leaving deployment confidence as an informal judgment, `deploy-confidence-service` turns rollout-relevant platform signals into a **repeatable, explainable deployment decision**.

It answers questions like:

- How confident are we that the cluster is safe for deployment right now?
- What is reducing deployment confidence?
- Should CI/CD continue, pause, or block this deployment?
- Can operators see both the decision and the reasons behind it?

### Why Prometheus and Grafana alone are not enough

Prometheus and Grafana are excellent at observability, but they are not the same thing as a deployment decision service.

Prometheus tells you:
- what the metrics are
- what changed
- what can be alerted on

Grafana shows you:
- how those signals look over time
- how to correlate them visually
- where to investigate

But neither one, on its own, gives you a consistent answer to:

**“Should we deploy now?”**

That decision usually remains manual.

An engineer still has to mentally combine:
- worker headroom
- restart pressure
- image pull health
- startup latency
- dependency reachability
- service freshness
- current operational context

and then interpret the result.

`deploy-confidence-service` adds that missing decision layer.

It sits on top of observability and transforms multiple low-level signals into:
- a deployment confidence score
- a decision state (`DEPLOY`, `CAUTION`, `HOLD`)
- a component-by-component explanation
- a historical decision trail
- an API that CI/CD pipelines can consume before rollout

So the distinction is simple:

- **Prometheus collects**
- **Grafana visualizes**
- **deploy-confidence-service decides**

### What the service does

`deploy-confidence-service` continuously evaluates rollout safety for a Kubernetes environment by combining telemetry, state, and dependency checks into a single operational decision model.

It currently:

- collects deployment-relevant signals from Prometheus
- reads Kubernetes pod and event data
- checks dependency health such as DNS and registry reachability
- computes a weighted deployment confidence score
- classifies the result as `DEPLOY`, `CAUTION`, or `HOLD`
- stores score history and component breakdowns in PostgreSQL
- exposes operational APIs through FastAPI
- provides human-readable visibility through Grafana
- supports CI/CD consumption as a pre-deploy confidence gate

The result is not just another monitoring view.

It is a **deployment decision intelligence service** that helps platform teams standardize rollout trust, explain deployment risk, and automate safer release behavior.


## Architecture Overview

`deploy-confidence-service` is designed as a **decision layer on top of Kubernetes observability**. It does not replace Prometheus, Grafana, or Kubernetes-native health signals. Instead, it consumes those signals, evaluates them against a scoring model, stores the result, and exposes a deployment-confidence decision that both humans and CI/CD systems can use.

At a high level, the service connects five concerns:

1. **Signal collection**
2. **Decision computation**
3. **Historical persistence**
4. **Human visibility**
5. **Deployment control**

### End-to-end flow

The system follows this operational flow:

1. **Prometheus** provides platform and workload metrics such as node pressure and restart-related signals.
2. **Kubernetes API** provides pod and event data such as recent image-pull failures and startup behavior.
3. **Dependency checks** validate deployment-critical external paths such as DNS resolution and registry reachability.
4. The **Deploy Confidence Service** gathers those raw inputs and passes them into the scoring engine.
5. The **scoring engine** normalizes each signal, applies weights, and computes:
   - component scores
   - final score
   - deployment status
   - summary explanation
6. The result is written to **PostgreSQL** as a historical score run with component-level detail.
7. **FastAPI endpoints** expose:
   - liveness
   - readiness
   - health
   - latest score
   - latest detailed breakdown
8. **Grafana** reads PostgreSQL and visualizes the current deployment decision, score trend, component breakdown, and score history.
9. A **consumer CI/CD pipeline** queries the service before deployment and blocks or allows rollout based on confidence policy.

### Architecture Diagram

![img](img/deploy-confidence-architecture.png)

### Major building blocks

The architecture is built around a few core layers.

1. Signal sources

These are the systems the service depends on for raw input.

- Prometheus 
  - source of platform and workload metrics 
  - used for node headroom and restart pressure signals
- Kubernetes API 
  - source of cluster state and recent operational events 
  - used for image pull failure and startup latency collection
- Dependency checks 
  - active checks performed by the service itself 
  - used for DNS and registry reachability validation

These systems provide the raw observability inputs, but they do not make the final deployment decision.

2. Deploy Confidence Service

This is the core application and the center of the architecture.

It is implemented as a FastAPI-based service and contains:

- collectors for Prometheus 
- collectors for Kubernetes signals 
- dependency-check logic 
- scoring engine 
- scheduler 
- persistence logic 
- API layer

This component continuously converts raw platform conditions into a deployment-confidence result.

3. Scoring and decision engine

The scoring engine is the logic layer that gives the system its purpose.

It:

- evaluates each component independently 
- normalizes raw signals into bounded scores
- applies weighted contribution rules
- computes the final score
- assigns a decision state:
  - `DEPLOY`
  - `CAUTION`
  - `HOLD`
- generates a short explanation summary

This is the layer that transforms observability into deployment decision intelligence.

4. PostgreSQL persistence layer

The service stores its output in PostgreSQL.

This gives the project:

- historical score tracking 
- dashboard-friendly querying 
- decision auditability 
- repeatable API output 
- traceable component breakdowns per score run

Instead of returning only an in-memory decision, the service keeps a durable record of:

- each calculated score run
- each component score within that run

This persistence layer is what makes trend analysis, Grafana visualization, and deployment audit possible.

5. API layer

The FastAPI API exposes the operational and decision interface of the service.

It is intentionally split between:

- process availability
- service readiness
- detailed operational health
- deployment decision outputs

This allows the service to be consumed by:

- Kubernetes probes
- engineers/operators
- dashboards
- CI/CD pipelines

The API is not just for monitoring. It is the machine-readable contract for deployment control.

6. Grafana dashboard

Grafana acts as the human-facing view of the decision system.

Rather than visualizing raw Prometheus signals directly for this use case, Grafana reads the service’s final stored outputs from PostgreSQL.

This allows operators to see:

- current deployment confidence
- deployment status
- score freshness
- latest component scores
- top risk factors
- score trend over time
- recent deployment decisions

This dashboard is the human explanation layer of the system.

7. CI/CD gate

The final architectural consumer is the deployment pipeline.

A consumer application pipeline can call:

- `/ready`
- `/health`
- `/score`
- `/details`

before deployment and evaluate whether rollout should continue.

This means the service is not just passive observability. It can actively influence release safety by blocking risky deployments before rollout begins.

### Why this architecture matters

This architecture separates responsibilities cleanly:

- Prometheus remains the metric source
- Kubernetes remains the state/event source
- PostgreSQL becomes the decision-history store
- Grafana becomes the operator decision dashboard
- FastAPI becomes the API contract for both humans and systems
- CI/CD becomes the enforcing consumer of deployment-confidence policy

This separation is important because it keeps the service focused on one job:

turning rollout-relevant platform signals into an explainable deployment decision

### Deployment model

The service is designed to run inside Kubernetes alongside the platform it evaluates.

That deployment model gives it:

- direct Kubernetes API access through service account and RBAC
- in-cluster access to Prometheus
- in-cluster access to PostgreSQL
- native readiness/liveness integration
- simple consumption by in-cluster workloads and pipelines

This makes the service itself a Kubernetes-native platform component, not an external script or one-off tool.

### Operational behavior

The architecture also includes a scheduler-based runtime loop.

The service:

- starts
- initializes tables
- performs an immediate score update
- starts a recurring scheduler
- recomputes and stores confidence on a fixed interval

This creates a continuous confidence stream rather than one-time checks.

As a result:

- Grafana always has fresh decision history
- API endpoints expose recent decisions
- readiness can depend on score freshness
- pipelines can trust that the decision is current

### Architecture outcome

> The result of this architecture is a platform service that sits between observability and delivery.
> It does not simply show what is happening.
> It answers a more operationally important question:
> Given the current platform state, how safe is it to deploy right now?
> That makes the architecture useful not only for visibility, but for real release-control decisions.


## Component Explanations

`deploy-confidence-service` is made up of several cooperating components, each with a specific role in the overall decision flow. Together, these components transform raw platform signals into a usable deployment decision that can be stored, visualized, and enforced in CI/CD.

This section explains each major component of the system and why it exists.

### 1. Prometheus Collector

The Prometheus collector is responsible for retrieving platform-level and workload-level metrics from Prometheus and converting them into raw scoring inputs.

Its purpose is to answer questions like:

- How much headroom do worker nodes currently have?
- Is restart pressure increasing?
- Are cluster signals suggesting safe or risky deployment conditions?

The Prometheus collector contributes raw data for components such as:

- **node headroom**
- **restart pressure**

It does not make decisions itself. It only retrieves and prepares input values that the scoring engine will later evaluate.

This separation is important because it keeps observability collection independent from policy logic.

### 2. Kubernetes Collector

The Kubernetes collector queries the Kubernetes API to retrieve deployment-relevant operational signals from pods and events.

Its purpose is to answer questions like:

- Are image pulls failing?
- Are workloads taking longer than normal to start?
- Is Kubernetes showing rollout-related warning signals?

The Kubernetes collector contributes raw data for components such as:

- **image pull health**
- **startup latency**

This collector is especially important because some rollout problems do not appear clearly in metrics alone. Kubernetes events and pod state often contain the operational signals that matter most during deployment.

### 3. Dependency Checks

The dependency-check component performs active validation of deployment-critical external paths.

Its purpose is to answer questions like:

- Is DNS resolution working?
- Are registries reachable?
- Can the platform still reach services required for deployment?

It contributes raw inputs for:

- **dependency health**

This component exists because a platform may look healthy from inside dashboards while still failing on the actual delivery path. A deployment target is only trustworthy if the dependencies required for deployment are still reachable.

### 4. Scoring Engine

The scoring engine is the core decision component of the system.

It takes the raw inputs from all collectors and transforms them into:

- component-level scores
- a final weighted score
- a deployment status
- a short explanation summary

Its job is to standardize deployment judgment.

Instead of relying on a person to mentally combine five different signals, the scoring engine applies one consistent evaluation model every time.

The scoring engine is responsible for:

- normalizing raw signals into bounded scores
- applying per-component weights
- calculating the overall deployment confidence score
- assigning one of:
  - `DEPLOY`
  - `CAUTION`
  - `HOLD`
- generating a summary explanation of the latest result

This is the component that turns observability into deployment decision logic.

### 5. PostgreSQL Persistence Layer

PostgreSQL stores the score history and component breakdowns generated by the service.

It provides durable storage for:

- final score runs
- per-component score details

The main tables are:

- `score_runs`
- `score_components`

This persistence layer matters because the service is not only meant to provide the latest score in memory. It must also provide:

- decision history
- trend analysis
- dashboard visualization
- auditability
- repeatable API results

Without PostgreSQL, the system would only provide transient decisions. With PostgreSQL, it becomes a historical decision service.

### 6. Scheduler

The scheduler is responsible for continuously recalculating deployment confidence at a fixed interval.

Its job is to make sure the service does not behave like a one-time check. Instead, it continuously maintains a fresh confidence stream.

The scheduler:

- starts when the service starts
- performs an initial score update on startup
- recalculates the score periodically
- persists each new result
- updates freshness state
- records failures when updates do not succeed

This is important because downstream consumers such as Grafana and CI/CD should be able to trust that the decision is recent.

The scheduler also supports operational correctness through freshness logic:
- a stale score should not be treated as trustworthy
- readiness should depend on fresh score generation
- degraded service health should be visible when updates fail

### 7. FastAPI API Layer

The FastAPI API is the operational and machine-readable interface of the service.

It exposes the service to:

- Kubernetes probes
- operators
- Grafana-backed workflows
- CI/CD pipelines
- external consumers that need the latest decision

The API exposes several kinds of endpoints:

- liveness
- readiness
- operational health
- decision output
- detailed score breakdown

This layer is important because the project is not just a background job. It is a service that other systems can consume directly.

The API is how deployment confidence becomes actionable.

### 8. Grafana Dashboard

Grafana is the human-facing observability layer for the final decision outputs of the service.

In this architecture, Grafana is not used to recompute the decision. Instead, it reads the service’s stored outputs from PostgreSQL and presents them as operational dashboards.

This allows operators to inspect:

- current deployment confidence
- deployment status
- score trend over time
- latest component scores
- top risk components
- recent decision history

Grafana provides the explanation and visibility layer for humans, while the API provides the interface for systems.

This distinction is important:
- Grafana explains the decision visually
- the service API exposes the decision programmatically

### 9. Consumer CI/CD Gate

The CI/CD gate is the deployment-control consumer of the service.

This is where the system becomes operationally powerful.

A consumer pipeline can call the service before deployment and use it to answer:

- Is the confidence score high enough for this environment?
- Is the service itself healthy and fresh?
- Should we continue, pause, or block rollout?

The pipeline can use endpoints such as:

- `/ready`
- `/health`
- `/score`
- `/details`

to enforce deployment policy.

This makes the service more than a dashboard or reporting tool. It becomes a pre-deploy safety control that can prevent risky rollouts before they happen.

### 10. How these components work together

Each component is intentionally narrow in responsibility.

- **Collectors** gather raw rollout-relevant signals
- **Dependency checks** validate critical deployment paths
- **Scoring engine** converts raw inputs into a decision
- **Scheduler** keeps that decision fresh over time
- **PostgreSQL** stores score history
- **FastAPI** exposes the service to machines and probes
- **Grafana** gives humans a visual operational view
- **CI/CD gate** consumes the result to control deployments

This separation is important because it keeps the system understandable, testable, and extensible.

Instead of one large opaque script, the service is built as a platform component with clear operational responsibilities.

### 11. Why this component model matters

This component breakdown is one of the reasons the project is useful as both a platform service and a portfolio project.

It shows that deployment safety is not handled by a single dashboard or one-off rule. It is handled by a system composed of:

- collection
- evaluation
- persistence
- visualization
- enforcement

> That makes the architecture realistic for platform engineering and SRE use cases. 
> The service is not just telling you what is happening. 
> It is telling you whether the platform is currently trustworthy enough to deploy.

---






## Scoring Model

The purpose of the scoring model is to turn several independent deployment-relevant signals into one consistent deployment-confidence decision.

Instead of relying on human judgment each time, the service evaluates a fixed set of components, converts each into a bounded score, applies weights, and produces:

- a **final deployment confidence score**
- a **decision state**
- a **component-by-component explanation**

This section explains what each score component means, why it matters, how the final score is derived, and how to interpret the decision states.

### Scoring philosophy

The scoring model is designed around one core idea:

**A platform can look generally healthy and still be a bad deployment target.**

That means the model should not only ask:
- is the cluster up?
- is CPU low?
- is Kubernetes responding?

It should also ask:
- are rollouts actually likely to succeed?
- are image pulls stable?
- are dependencies reachable?
- are workloads starting cleanly?
- is the platform under pressure that could reduce rollout safety?

The model therefore evaluates **deployment confidence**, not just general platform health.

### Current scoring components

The service currently evaluates five components:

1. **node headroom**
2. **restart pressure**
3. **image pull health**
4. **startup latency**
5. **dependency health**

Each component contributes to the final score through a weighted model.

---

### 1. Node Headroom

#### What it measures
Node headroom measures how much usable capacity remains on worker nodes.

It focuses on whether deployment targets still have enough CPU and memory headroom to absorb rollout activity safely.

#### Why it matters
A deployment can fail or behave unpredictably if nodes are already under pressure.

Even if the cluster is technically running, low headroom can increase the risk of:
- scheduling contention
- slower pod placement
- pod startup degradation
- eviction pressure
- poor rollout behavior under load

#### What a high score means
A high node headroom score means:
- worker nodes have reasonable CPU headroom
- worker nodes have reasonable memory headroom
- the platform is less likely to resist new workload placement

#### What a low score means
A low node headroom score means:
- one or more workers are already stressed
- rollout activity may increase contention
- the cluster may not be a good deployment target right now

---

### 2. Restart Pressure

#### What it measures
Restart pressure measures whether workloads are restarting unusually often within the observation window.

It is meant to capture instability that may not yet be visible in broader cluster health.

#### Why it matters
If restart activity is elevated, the platform may already be unstable.

That can indicate:
- crashing workloads
- dependency instability
- rollout regressions
- unhealthy control paths
- broader operational turbulence

A platform with high restart pressure may still look “green” in many dashboards, but it is often a poor time to deploy additional change.

#### What a high score means
A high restart pressure score means:
- few recent restarts
- low evidence of workload instability
- less reason to distrust rollout safety

#### What a low score means
A low restart pressure score means:
- restarts are increasing
- instability may already be present
- deployment confidence should be reduced

---

### 3. Image Pull Health

#### What it measures
Image pull health measures whether recent image pulls are succeeding or failing.

It is derived from Kubernetes events such as:
- `ErrImagePull`
- `ImagePullBackOff`
- recent pull-related failure messages

#### Why it matters
This is one of the most deployment-specific signals in the entire model.

A cluster may be healthy in general, but if the runtime path to registries is unstable, then deployment confidence should drop immediately.

This component helps catch cases where:
- the delivery path is degraded
- registry access is unreliable
- DNS or transport behavior is misleading
- deployment failures are likely even though the control plane looks healthy

#### What a high score means
A high image pull health score means:
- recent image pulls are succeeding
- registry path appears healthy
- rollout artifact delivery is likely to work

#### What a low score means
A low image pull health score means:
- image pull failures were detected recently
- deployment safety is reduced
- new rollouts may fail at the runtime pull stage

This component is especially important because it directly captures whether the cluster can actually obtain the artifacts required for deployment.

---

### 4. Startup Latency

#### What it measures
Startup latency measures how long pods take to move from creation to startup.

The current MVP uses pod timestamps to estimate startup behavior and compute a rollout-oriented latency signal.

#### Why it matters
Even when deployments technically succeed, elevated startup latency can signal underlying delivery friction.

That can be caused by:
- slow image pulls
- slow scheduling
- storage delays
- node pressure
- transient cluster instability

Startup latency is therefore a useful deployment-confidence signal because it reflects rollout responsiveness, not just binary success/failure.

#### What a high score means
A high startup latency score means:
- recent startup times are within acceptable bounds
- rollout behavior is responsive
- deployment timing is less likely to degrade release confidence

#### What a low score means
A low startup latency score means:
- pods are taking longer than expected to start
- rollout quality may be degraded
- deployment confidence should decrease

---

### 5. Dependency Health

#### What it measures
Dependency health measures whether critical deployment dependencies are reachable.

The current implementation checks paths such as:
- DNS resolution
- registry reachability

#### Why it matters
This component exists because deployment failures often happen below the layer that dashboards emphasize.

A cluster can appear healthy while:
- DNS is intermittently failing
- registry paths are unstable
- required dependencies are unreachable
- rollout paths are degraded

Dependency health is therefore a trust signal for the underlying delivery path.

#### What a high score means
A high dependency health score means:
- DNS resolution is working
- registry endpoints are reachable
- deployment-critical paths appear available

#### What a low score means
A low dependency health score means:
- dependency path validation failed
- rollout safety is significantly reduced
- deployments may fail even if the broader cluster looks healthy

---

## Weighted scoring model

Each component contributes to the final score through a weight.

The weights express how strongly each signal should influence the deployment decision.

The current model uses:

- **node headroom** → `0.25`
- **restart pressure** → `0.20`
- **image pull health** → `0.25`
- **startup latency** → `0.15`
- **dependency health** → `0.15`

### Why these weights were chosen

The weight model emphasizes signals that are closest to actual deployment success:

- **node headroom** matters because insufficient capacity can degrade rollout reliability
- **image pull health** matters because deployment cannot succeed if artifacts cannot be pulled
- **restart pressure** matters because existing instability reduces trust in new change
- **startup latency** matters because rollout responsiveness is part of deployment safety
- **dependency health** matters because hidden path failures can break rollout even when the platform looks healthy

This gives the model a bias toward **release trust**, not just infrastructure uptime.

---

## Final score calculation

The final deployment confidence score is calculated as the weighted combination of all component scores.

In simplified form:

```text
final_score =
  (node_headroom_score × 0.25) +
  (restart_pressure_score × 0.20) +
  (image_pull_health_score × 0.25) +
  (startup_latency_score × 0.15) +
  (dependency_health_score × 0.15)
```

The output is a bounded score from 0 to 100.

Score interpretation
- 0–69.99 → low confidence
- 70–84.99 → moderate confidence
- 85–100 → strong confidence

These ranges are reflected both in API output and in Grafana thresholds.

### Deployment decision states

The service does not return only a score. It also assigns a decision state.

The current states are:

- `DEPLOY`
- `CAUTION`
- `HOLD`

### DEPLOY
Meaning

The platform currently looks safe enough for deployment based on the observed signals.

Interpretation

This means:

- no major deployment-risk signal is dominating
- rollout-relevant conditions are acceptable
- the confidence score is strong enough to proceed

This does not mean the deployment is guaranteed to succeed. It means current platform conditions support deployment with acceptable confidence.

### CAUTION
Meaning

The platform is not clearly unsafe, but deployment confidence is reduced.

Interpretation

This means:

- one or more components are weak enough to lower trust
- deployment might still succeed
- additional review, lower-risk rollout strategy, or environment-specific caution may be appropriate

This state is useful because platform reality is not always binary. Some conditions do not justify an outright block, but they do justify increased care.

In CI/CD policy, `CAUTION` can be:

- `allowed in dev`
- `allowed in staging with review`
- `blocked in prod`

### HOLD
Meaning

Deployment confidence is too low to proceed safely.

Interpretation

This means:

- one or more deployment-critical signals are degraded enough to block trust
- rollout risk is too high
- the environment should be investigated before change continues

`HOLD` is meant to be a strong operational signal:
do not continue deployment until the current state is understood or corrected.

Deploy allowed flag

In addition to score and status, the service also produces a `deploy_allowed` flag.

This is the machine-friendly summary of the decision.

It exists because downstream systems such as CI/CD pipelines should not have to reinterpret the full scoring model on their own.

A pipeline can consume:

- `score`
- `status`
- `deploy_allowed`

and then apply environment-specific policy on top.

This makes the service easier to use as a deployment gate.

### Summary explanation

Each score run includes a short summary string.

Its purpose is to explain, in plain language, what is reducing deployment confidence.

Example themes include:

- image pull health reduced rollout confidence
- startup latency is elevated
- worker headroom is moderate
- dependency checks are healthy

This summary is intended for:

- operators reading Grafana
- engineers checking API output
- pipeline logs
- deployment reviews

It provides a fast human explanation of the latest decision.

### Why the scoring model matters

The scoring model is what makes the project more than a dashboard.

Without the scoring model, operators still have to combine several independent signals manually.

With the scoring model, the system provides:

- one consistent evaluation method
- one final confidence score
- one explainable deployment state
- one machine-readable decision output

That means the service can be used not only to observe risk, but to standardize how deployment risk is interpreted across environments.

### What this model is and what it is not

This model is:

- a rollout-confidence model
- a deployment-decision model
- a structured interpretation layer on top of observability

This model is not:

- a machine learning predictor
- a guarantee of deployment success
- a replacement for incident judgment
- a replacement for raw observability tools

Its purpose is to make deployment trust more consistent, explainable, and automatable.

### Current model limitations

Like any scoring model, this one is only as good as its signal design and threshold tuning.

Current limitations include:

- startup latency is an MVP approximation and can be refined further
- thresholds may need adjustment for different clusters
- some environments may require different weights
- policy interpretation may vary by environment or risk tolerance

That is acceptable for this stage of the project because the model is intentionally transparent and adjustable.

The important thing is that it already provides a strong, structured deployment-confidence baseline.

### Why this scoring model is useful in practice

In practice, this model helps answer a question most teams still handle informally:

Is the platform trustworthy enough to deploy right now?

By turning that question into:

- measured inputs
- weighted evaluation
- persistent history
- visible dashboards
- CI/CD-enforceable decisions

> the model gives platform teams a more operationally mature way to reason about rollout safety.


## Score Lifecycle and Storage

A deployment-confidence result is not useful only at the moment it is calculated. It also needs to be:

- **repeatable**
- **traceable**
- **historical**
- **queryable**
- **explainable over time**

That is why `deploy-confidence-service` does not stop at computing an in-memory score. It persists every calculated result as a **score run** and stores each component that contributed to that result.

This section explains how score generation works over time, what a score run means, how the service stores results, and why historical storage is important.

### What a score run is

A **score run** is one complete execution of the deployment-confidence evaluation cycle.

In one score run, the service:

1. collects raw signals from Prometheus
2. collects rollout-related Kubernetes state and events
3. performs dependency checks
4. computes each component score
5. computes the final weighted score
6. assigns a deployment status
7. writes the result to PostgreSQL

A score run is therefore the full record of one deployment-confidence decision at a specific point in time.

It is not just a number. It is a structured snapshot of deployment trust for that moment.

### Why score runs exist

Score runs exist because deployment confidence is a **time-dependent operational signal**.

A single score only answers:

- what is the confidence right now?

A score history answers more useful operational questions such as:

- Has confidence been stable over the last hour?
- Did deployment confidence degrade gradually or suddenly?
- Which component keeps dragging the score down?
- Was the platform already unhealthy before deployment was attempted?
- Was a blocked deployment decision justified by the signals at that time?

Without score history, the service would be much less useful for:
- operators
- dashboards
- post-incident review
- deployment audit
- CI/CD troubleshooting

### How often score runs are generated

The service uses a scheduler to generate score runs on a fixed interval.

The lifecycle is:

- service starts
- database tables are initialized
- an immediate score update is executed
- the recurring scheduler starts
- new score runs are written periodically

The current scheduler interval is controlled by configuration and is designed to keep the score fresh enough for both dashboards and CI/CD use.

That means the service does not behave like an on-demand script. It behaves like a continuously running decision system.

### Why freshness matters

A deployment-confidence decision is only trustworthy if it is recent.

A stale score can be misleading because platform conditions may have changed after the last update.

That is why the service tracks:

- last successful score update
- whether the score is still fresh
- scheduler health
- recent error state

Freshness is part of the service’s operational contract.

This is also why readiness depends on more than process health:
- the API can be alive
- the scheduler can be running
- but if score updates are failing or stale, the service should not be treated as fully ready for decision consumption

### Storage model

The service persists score data in PostgreSQL using two main tables:

- `score_runs`
- `score_components`

These two tables form the core of the system’s decision history.

---

## `score_runs`

The `score_runs` table stores one row per score execution.

Each row represents the final decision output for one moment in time.

Typical fields include:

- `id`
- `calculated_at`
- `total_score`
- `status`
- `deploy_allowed`
- `threshold`
- `summary`

### What `score_runs` represents

This table answers:

- What was the final deployment confidence score?
- What status was assigned?
- Was deployment allowed?
- What was the summary explanation?
- When was this decision calculated?

This is the top-level decision history of the service.

It is what powers:
- the latest score API
- the score trend dashboard
- recent deployment decision history
- CI/CD gate inspection

### Why `score_runs` matters

This table turns the service into a historical decision engine instead of a transient evaluator.

It allows operators and pipelines to inspect not only the current state, but the timeline of previous decisions.

---

## `score_components`

The `score_components` table stores one row per component within each score run.

For every score run, the service stores the detailed breakdown of how that final score was formed.

Typical fields include:

- `id`
- `score_run_id`
- `component_name`
- `component_score`
- `weight`
- `reason`
- `raw_payload`

### What `score_components` represents

This table answers:

- Which components contributed to the final score?
- What score did each component receive?
- What weight did each component carry?
- Why did the component receive that score?
- What raw data was used to compute it?

This is the explainability layer of the persistence model.

### Why `score_components` matters

Without this table, the service would only return a final score and status.

That would be useful, but incomplete.

With `score_components`, the system can explain:
- what reduced confidence
- what remained healthy
- which component was the main deployment risk
- how the final result was composed

This is the foundation for:
- Grafana component breakdown panels
- top risk component tables
- detailed API responses
- pipeline failure explanations

---

## Relationship between `score_runs` and `score_components`

The relationship is simple:

- one `score_run` has many `score_components`
- each `score_component` belongs to one `score_run`

This means every top-level decision can be expanded into a fully explainable breakdown.

For example:

- one row in `score_runs`
- five related rows in `score_components`

corresponding to:

- node headroom
- restart pressure
- image pull health
- startup latency
- dependency health

That makes the stored result both compact and explainable.

---

## Score lifecycle from collection to storage

The score lifecycle can be described as:

1. **scheduler triggers evaluation**
2. **collectors gather raw inputs**
3. **scoring engine computes component scores**
4. **scoring engine computes final score and status**
5. **service writes one row to `score_runs`**
6. **service writes one row per component to `score_components`**
7. **APIs and Grafana read the latest and historical results**

This makes PostgreSQL the durable memory of the service.

### End-to-end score storage flow

![img](img/score-lifecycle.png)


### Why historical storage is important

Historical storage gives the project several major capabilities.

1. Trend analysis

It allows the service to show whether deployment confidence is:

- improving
- degrading
- oscillating
- stable

This is much more useful than a one-time score.

### 2. Explainability over time

It allows operators to see:

- which components repeatedly degrade confidence
- whether the same risk pattern keeps returning
- whether current problems are new or recurring

### 3. Dashboarding

Grafana depends on persistent score history to show:

- score over time
- component scores over time
- recent decisions
- latest breakdown

### 4. CI/CD accountability

If a deployment is blocked, historical storage allows teams to answer:

- what was the score at the time?
- what caused the block?
- was the decision reasonable?
- what had degraded?

### 5. Incident and release review

Historical storage supports post-deployment and post-incident analysis.

It becomes possible to ask:

- was the environment already weak before rollout?
- did image pull health degrade before the incident?
- did startup latency worsen leading into the deployment?

That makes the service valuable beyond real-time gating.

### What gets stored with each score run

Each evaluation cycle stores both decision and explanation.

Final decision data

Stored in score_runs:

- final score
- status
- deploy allowed
- threshold
- summary
- calculation timestamp
- Component breakdown data

Stored in score_components:

- component name
- component score
- weight
- reason
- raw payload

This balance is important:

- score_runs gives fast decision history
- score_components gives detailed explanation

### Why raw payload storage matters

Each component stores a raw_payload field so the system can preserve the inputs that shaped the score.

This makes the service much more transparent.

For example, a component may record raw values such as:

- max worker CPU percentage
- max worker memory percentage
- recent restart count
- pull failures in the last window
- affected registries
- measured startup latency
- DNS and registry check results

That makes it easier to:

- debug the scoring model
- validate correctness
- inspect unexpected results
- support future threshold tuning

This is especially useful during development and operational review.

### Latest result vs historical results

The service supports both:

- the latest score
- the history of previous scores

This distinction matters.

### Latest result

Used for:

- `/score`
- `/details`
- `CI/CD gating`
- readiness/freshness interpretation

### Historical results

Used for:

- Grafana trends
- decision audit
- operator investigation
- release confidence analysis over time

A good deployment-confidence service needs both.

### Why the storage model is production-style

The persistence model is simple, but operationally strong.

It provides:

- clear separation between summary and detail
- durable history
- support for dashboards
- support for API consumers
- support for CI/CD gating
- support for explainability
- support for future tuning

> This is why the project feels like a platform service instead of a one-off script.
> The service is not just calculating a score.
> It is maintaining a historical record of deployment trust.

### What this lifecycle enables

Because the service continuously generates, stores, and exposes score runs, it becomes possible to build:

- current deployment decision dashboards
- score trend dashboards
- component trend dashboards
- deployment audit history
- pre-deploy CI/CD gates
- richer incident review workflows

That makes score lifecycle and storage one of the most important foundations of the entire system.

Without it, the service would only answer:

- what is the score right now?

With it, the service can answer:

- what is the score now?
- how did we get here?
- has confidence been changing?
- what repeatedly reduces rollout trust?
- should this deployment be blocked based on recent evidence?

That is the real value of the persistence layer.


## API Reference

![reference](img/api-reference.png)

`deploy-confidence-service` exposes a small set of HTTP endpoints that separate **process health**, **service readiness**, **operational health**, and **deployment decision output**.

This separation is intentional.

Different consumers need different kinds of answers:

- Kubernetes probes need to know whether the process is alive
- operators need to know whether the service is healthy and fresh
- CI/CD pipelines need to know whether a deployment should proceed
- dashboards need access to current decision and explanation data

The API is therefore structured to support both **operational correctness** and **deployment decision consumption**.

### Base assumption

All endpoints are exposed by the FastAPI service and return JSON.

- Typical in-cluster service URL:

```text
http://deploy-confidence-service.deploy-confidence.svc.cluster.local:8000
```
- Typical local port-forward URL:
```shell
http://localhost:8000
```
### Simplified Flow
```text
Client / Operator --------\
                           \
CI/CD Pipeline -------------> FastAPI API ---------> PostgreSQL ---------> Grafana Dashboard
                             /live
                             /ready
                             /health
                             /score
                             /details

                    In-cluster: http://deploy-confidence-service.deploy-confidence.svc.cluster.local:8000
                    Local:      http://localhost:8000

Note: Score history is written internally by the scheduler and scoring engine.
```

### 1. `GET /live`
### Purpose

`/live` is the liveness endpoint.

It answers one narrow question:

Is the application process alive?

It is intended primarily for:

- Kubernetes liveness probes
- simple process availability checks

It should remain lightweight and should not depend on:

- database connectivity
- scheduler freshness
- score calculation success

### Why it exists

>A liveness endpoint should tell Kubernetes whether the process is alive enough to keep running.
> If the app process is wedged or unresponsive, liveness should fail and Kubernetes can restart the container.

- Example response
```json
{
  "status": "alive",
  "service": "deploy-confidence-service"
}
```
### When to use it

Use `/live` when you need to know:

- whether the process is up
- whether the container should keep running

Do not use `/live` to judge whether the service is trustworthy for deployment decisions.

### 2. `GET /ready`
### Purpose

`/ready` is the readiness endpoint.

It answers a stricter question:

Is this service instance ready to serve trustworthy deployment-confidence results?

It is intended primarily for:

- Kubernetes readiness probes
- operational checks before traffic should be routed
- CI/CD prechecks when service trust matters

### What it evaluates

`/ready` currently evaluates whether:

- the database is reachable
- the scheduler has started
- the latest successful score is still fresh

### Why it exists

A process can be alive but not yet operationally ready.

Examples:

- the API started but database connectivity failed
- the scheduler is not running yet
- the service has not produced a fresh score recently
- readiness should be withheld until the service can produce trustworthy results

Example healthy response
```json
{
  "ready": true,
  "database_healthy": true,
  "scheduler_healthy": true,
  "score_fresh": true
}
```
Example unhealthy response
```json
{
  "ready": false,
  "database_healthy": true,
  "scheduler_healthy": true,
  "score_fresh": false
}
```

In unhealthy cases, the endpoint should return 503 Service Unavailable.

### When to use it

Use `/ready` when you need to know:

- whether Kubernetes should route traffic to this pod
- whether the service is operationally usable right now
- whether CI/CD should trust this service as a deployment gate

### 3. `GET /health`
### Purpose

/health is the full operational health endpoint.

It answers a broader question:

What is the current health state of the service, and why?

It is intended for:

- operators
- dashboards
- troubleshooting
- CI/CD prechecks that need more than a binary response

### What it returns

`/health` provides a richer operational summary including:

- overall health status
- application health
- database health
- scheduler health
- score freshness
- last successful score update
- last scheduler start/failure timestamps
- last error state
- service version

### Why it exists

A deployment-confidence service must itself be trustworthy.

A simple “up/down” check is not enough.

Operators need to know:

- is the scheduler running?
- are score updates still fresh?
- when was the last successful update?
- did the last scoring attempt fail?
- is the service degraded or truly healthy?

Example healthy response
```json
{
  "status": "ok",
  "service": "deploy-confidence-service",
  "app_healthy": true,
  "database_healthy": true,
  "scheduler_healthy": true,
  "score_fresh": true,
  "last_successful_score_update": "2026-03-31T12:55:42.210583Z",
  "last_run_started_at": "2026-03-31T12:55:40.439446Z",
  "last_run_failed_at": null,
  "last_error": null,
  "version": "0.1.0"
}
```
Example degraded response
```json
{
  "status": "degraded",
  "service": "deploy-confidence-service",
  "app_healthy": true,
  "database_healthy": true,
  "scheduler_healthy": true,
  "score_fresh": false,
  "last_successful_score_update": "2026-03-31T10:00:00Z",
  "last_run_started_at": "2026-03-31T12:00:00Z",
  "last_run_failed_at": "2026-03-31T12:00:00Z",
  "last_error": "Prometheus query failed: [Errno 111] Connection refused",
  "version": "0.1.0"
}
```
### Status meanings

Typical values include:

- `ok`
- `degraded`
- `failed`

These statuses reflect the operational state of the service, not the deployment confidence score itself.

When to use it

Use `/health` when you need:

- detailed operational state
- failure context
- freshness visibility
- a richer service-trust signal than /live or /ready
### 4. `GET /score`
### Purpose

`/score` is the primary deployment decision endpoint.

It answers the core question:

What is the current deployment confidence result?

It is intended for:

- CI/CD deployment gates
- operators
- release tooling
- lightweight dashboards or scripts

### What it returns

`/score` returns the latest stored deployment-confidence decision, including:

- final score
- status
- deploy allowed flag
- threshold
- short summary
- update timestamp

### Why it exists

This endpoint provides the compact, machine-friendly form of the deployment-confidence decision.

It is the endpoint most consumers should call first.

Example response
```json
{
  "score": 78.5,
  "status": "CAUTION",
  "deploy_allowed": true,
  "threshold": 70,
  "summary": "Image pull health and startup latency reduced rollout confidence.",
  "updated_at": "2026-03-31T07:43:35.624179Z"
}
```
### Field meanings
`score`

- The final weighted deployment-confidence score from 0 to 100.

`status`

- The decision state:

  - `DEPLOY`
  - `CAUTION`
  - `HOLD`
  
`deploy_allowed`

- A machine-friendly boolean indicating whether deployment is currently allowed by the service’s decision model.

`threshold`

- The threshold used for interpretation in the current run.

`summary`

- A short human-readable explanation of what influenced the result most.

`updated_at`

- The timestamp of the latest score run.

### When to use it

Use `/score` when you need:

- the latest deployment decision
- a fast pre-deploy check
- a compact summary for scripts and pipelines

This is the most important endpoint for CI/CD integration.

### 5. `GET /details`
### Purpose

`/details` is the full decision explanation endpoint.

It answers the question:

Why is the current score what it is?

It is intended for:

- operators
- dashboards
- CI/CD failure explanation
- debugging and model validation

### What it returns

`/details` returns everything from `/score`, plus the full component breakdown for the latest score run.

This includes, for each component:

- component name
- component score
- weight
- reason
- raw payload

### Why it exists

A final score is useful, but often not sufficient.

Operators and pipelines need to know:

- what reduced confidence
- which component is the main risk
- what raw conditions were observed
- how the score was composed

That is what `/details` provides.

Example response
```json
{
  "score": 78.5,
  "status": "CAUTION",
  "deploy_allowed": true,
  "threshold": 70,
  "summary": "Image pull health and startup latency reduced rollout confidence.",
  "updated_at": "2026-03-31T07:43:35.624179Z",
  "components": [
    {
      "name": "node_headroom",
      "score": 82.0,
      "weight": 0.25,
      "reason": "Workers have moderate CPU and memory headroom.",
      "raw": {
        "max_worker_cpu_pct": 61,
        "max_worker_mem_pct": 67
      }
    },
    {
      "name": "restart_pressure",
      "score": 90.0,
      "weight": 0.20,
      "reason": "Restart pressure is low across monitored workloads.",
      "raw": {
        "recent_restarts_15m": 1
      }
    },
    {
      "name": "image_pull_health",
      "score": 45.0,
      "weight": 0.25,
      "reason": "Recent image pull failures reduced rollout confidence.",
      "raw": {
        "pull_failures_15m": 3,
        "affected_registries": ["quay.io"]
      }
    },
    {
      "name": "startup_latency",
      "score": 70.0,
      "weight": 0.15,
      "reason": "Pod startup latency is elevated but still within tolerable range.",
      "raw": {
        "p95_startup_seconds": 48
      }
    },
    {
      "name": "dependency_health",
      "score": 95.0,
      "weight": 0.15,
      "reason": "Critical deployment dependencies are currently reachable.",
      "raw": {
        "dns_ok": true,
        "registry_ok": true
      }
    }
  ]
}
```
### When to use it

Use `/details` when you need:

- component-level explanation
- the top deployment risks
- richer failure output in CI/CD
- detailed operator troubleshooting

This is the most useful endpoint for understanding why a deployment-confidence decision was made.

### Endpoint usage summary
Use `/live` for:
- process liveness
- Kubernetes liveness probes

Use `/ready` for:
- Kubernetes readiness probes
- service operational readiness
- simple pre-deploy service trust checks

Use `/health` for:
- operational troubleshooting
- scheduler and freshness visibility
- detailed service state

Use `/score` for:
- CI/CD deployment gates
- lightweight decision checks
- simple decision retrieval

Use `/details` for:
- full explanation
- top risk analysis
- debugging and dashboard breakdowns

### Example operational flow

A typical consumer such as a CI/CD pipeline may use the API like this:

- call `/ready`
- call `/health`
- verify score freshness and service status
- call `/score`
- compare score to environment threshold
- call `/details` if a richer explanation is needed
- decide whether to deploy or block

This flow is important because it treats the service not just as a score generator, but as a trusted operational dependency.

Why this API design matters

The API is intentionally split because deployment decision systems need both:

- process-level health
- service-level trust
- decision-level output
- explanation-level detail

A single endpoint would not serve all of those needs cleanly.

This design makes the service usable by:

- Kubernetes
- operators
- dashboards
- pipelines
- future automation

In other words, the API is not just a convenience layer.

It is the contract that turns deployment confidence into something both humans and systems can rely on.





















## Health, Readiness, and Liveness Semantics

`deploy-confidence-service` separates **liveness**, **readiness**, and **health** so that different consumers can ask different operational questions without overloading a single endpoint.

This separation is important because a deployment-confidence service must be trusted not only as a running process, but as a **fresh and operationally correct decision system**.

A service can be:
- alive, but not ready
- ready once, but later stale
- running, but degraded
- healthy enough for probes, but not healthy enough for CI/CD trust

That is why the service exposes:
- `/live`
- `/ready`
- `/health`

Each endpoint has a different meaning and a different operational purpose.

---

## Why this distinction matters

Many services expose one generic health endpoint and use it for everything.

That approach is usually too coarse for a system like this.

`deploy-confidence-service` is not a passive API. It is a continuously updating decision engine. That means process availability alone is not enough.

For example:

- the API may be alive, but PostgreSQL may be unavailable
- PostgreSQL may be available, but the scheduler may not be running
- the scheduler may be running, but score updates may have failed recently
- the latest stored score may be stale and no longer trustworthy

In those cases, simply reporting “up” would be misleading.

This is why liveness, readiness, and health must be separated.

---

## `/live` — Liveness semantics

### What it means

`/live` answers one narrow question:

**Is the application process alive?**

This endpoint is intentionally lightweight.

It does not try to determine:
- whether the database is reachable
- whether the scheduler is healthy
- whether the score is fresh
- whether the service is trustworthy for deployment decisions

It only indicates whether the process is running and responding.

### Why it exists

The purpose of liveness is to support container lifecycle management.

Kubernetes should use liveness to decide:
- should this container keep running?
- or is it stuck badly enough that it should be restarted?

A liveness check must therefore remain simple and avoid depending on fragile downstream systems.

### What it should depend on

`/live` should depend only on:
- application process responsiveness
- ability to return a minimal successful response

It should **not** fail just because:
- PostgreSQL is down
- Prometheus is unavailable
- the scheduler is degraded
- the score has become stale

Those conditions matter for readiness and health, not for liveness.

### Operational interpretation

If `/live` fails:
- the service process is likely unhealthy
- Kubernetes may restart the container

If `/live` succeeds:
- the process is alive
- but the service may still not be operationally ready

---

## `/ready` — Readiness semantics

### What it means

`/ready` answers a stricter question:

**Is this service instance ready to serve trustworthy deployment-confidence results right now?**

Readiness is about whether the service is usable as an operational dependency.

### Why it exists

A service can be alive but not ready.

Examples:
- database connection failed
- scheduler has not started
- no fresh score is available
- startup sequence has not finished
- score update path is not functioning

In these cases, traffic or deployment-decision trust should not be routed to the service yet.

### What `/ready` evaluates

In the current implementation, readiness depends on:

- **database health**
- **scheduler health**
- **score freshness**

A ready service instance must be able to:
- access PostgreSQL
- run its scheduler
- provide a recent score that is still trustworthy

### What “score freshness” means

A deployment-confidence decision is only useful if it is recent.

If the service has not successfully updated its score for too long, the result should be considered stale.

The current freshness logic treats a score as fresh only if the last successful score update is still within the configured acceptable age window.

That means readiness is not just about startup success. It is also about **ongoing operational freshness**.

### Response behavior

If readiness conditions are satisfied:
- `/ready` returns `200 OK`

If readiness conditions are not satisfied:
- `/ready` returns `503 Service Unavailable`

This is useful because Kubernetes can use the response directly to determine whether the pod should receive traffic.

### Operational interpretation

If `/ready` fails:
- the service should not yet be trusted as a deployment-decision source
- Kubernetes should avoid routing readiness-dependent traffic to it
- CI/CD should not use it as a confidence gate

If `/ready` succeeds:
- the service is operationally usable
- the latest confidence state is considered fresh enough to trust

---

## `/health` — Health semantics

### What it means

`/health` answers the broadest question:

**What is the overall operational state of the service, and why?**

It is the most informative health endpoint and is intended for:
- operators
- troubleshooting
- dashboards
- CI/CD prechecks that need context
- service introspection

### Why it exists

A binary ready/not-ready answer is useful, but often not sufficient.

Operators need to understand:
- whether the service is healthy, degraded, or failed
- whether scheduler updates are succeeding
- when the last good score was written
- whether the last run failed
- whether stale data is the reason the service is degraded

That is what `/health` provides.

### What `/health` exposes

The current health response includes fields such as:

- `status`
- `app_healthy`
- `database_healthy`
- `scheduler_healthy`
- `score_fresh`
- `last_successful_score_update`
- `last_run_started_at`
- `last_run_failed_at`
- `last_error`
- `version`

This makes `/health` the richest operational endpoint in the service.

---

## Health status meanings

The `status` field in `/health` is intentionally more expressive than simple up/down.

It can currently represent:

- `ok`
- `degraded`
- `failed`

### `ok`

`ok` means the service is functioning as intended.

Typical conditions:
- application is healthy
- database is healthy
- scheduler is running
- score is fresh
- no current scheduler error is blocking trust

This is the desired steady state.

### `degraded`

`degraded` means the service is still reachable, but its trustworthiness or correctness is reduced.

Typical examples:
- scheduler is running but the score is stale
- database is reachable but the last score update failed
- the service is alive, but not fully operational for decision trust
- a recent error has occurred that should not be ignored

This is one of the most important states in the service because it reflects the reality that operational systems are not always simply healthy or dead.

A degraded state means:
**the service is present, but caution is required when trusting its outputs.**

### `failed`

`failed` means the service is in a more fundamental error state.

Typical examples:
- database is unreachable
- critical operational dependency is unavailable
- service can no longer provide meaningful decision capability

This state indicates the service should not be trusted for deployment decision consumption.

---

## Freshness semantics

### Why freshness is part of health

For many services, freshness is irrelevant.

For `deploy-confidence-service`, freshness is essential.

A deployment score is not timeless. It reflects the platform state at the time it was computed.

If the service has not updated successfully for too long, then:
- dashboards may show outdated decisions
- pipelines may trust stale confidence
- operators may misread platform safety

That is why freshness is part of both:
- readiness
- health

### What stale means operationally

A stale score means:

- the service is no longer keeping up with current platform state
- the latest score may not reflect current rollout conditions
- deployment decisions based on it may be misleading

This is why a stale score should reduce trust, even if the API is still responsive.

---

## Scheduler semantics

### Why scheduler health matters

This service depends on a scheduler because the score is generated continuously.

The scheduler is not an optional background convenience. It is part of the service’s operational contract.

If the scheduler is not working:
- score updates stop
- freshness will eventually fail
- dashboards become outdated
- pipelines may lose trust in the service

### What scheduler-healthy means

A healthy scheduler state means:
- the scheduler has started successfully
- the service is capable of executing update cycles
- score generation is operationally active

### What scheduler failure means

A scheduler problem may indicate:
- background jobs are no longer running
- score runs are no longer being created
- the service may still respond, but not fulfill its purpose

That is why scheduler health is exposed explicitly.

---

## Last error semantics

### Why last error is exposed

Operational trust requires context.

If the service is degraded, operators and pipelines should be able to understand why.

The `last_error` field helps explain:
- recent collector failures
- database write issues
- Prometheus connectivity problems
- scheduler execution failures

This is especially useful when:
- `/ready` is failing
- score freshness is false
- `/health` status is degraded

### Why this matters

A service that only says “degraded” is harder to operate.

A service that says:
- degraded
- last error = Prometheus query failed
- score stale
- last successful update = 20 minutes ago

is much easier to reason about.

---

## Probe design rationale

The probe design is intentionally split like this:

### Liveness probe
Uses:
- `/live`

Because Kubernetes should restart the pod only when the process is unhealthy, not just because the database or scheduler had temporary issues.

### Readiness probe
Uses:
- `/ready`

Because traffic and trust should only be routed when the service is operationally ready and score freshness is intact.

### Health endpoint
Used for:
- operators
- dashboards
- CI/CD diagnostics
- troubleshooting

Because it gives the full explanation of the service state.

This is a stronger design than pointing all probes at one generic health endpoint.

---

## CI/CD interpretation of health semantics

The CI/CD gate should not rely on `/live`.

A deployment gate should typically care about:
- `/ready`
- `/health`
- `/score`
- `/details`

A reasonable CI/CD sequence is:

1. check `/ready`
2. check `/health`
3. ensure `status == ok`
4. ensure `score_fresh == true`
5. query `/score`
6. optionally query `/details` for explanation

This ensures the pipeline is not using stale or degraded service output.

---

## Human interpretation of health semantics

For operators, the meaning is:

- **`/live`** tells you whether the container is alive
- **`/ready`** tells you whether the service is trustworthy enough to serve current decision traffic
- **`/health`** tells you why the service is healthy, degraded, or failed

This makes the service easier to run in production-style environments.

---

## Why these semantics matter for the project

These semantics are important because they demonstrate that the service was designed as a real operational component, not just a proof-of-concept API.

They show attention to:
- correctness
- freshness
- service trust
- operational degradation
- Kubernetes-native probe behavior
- CI/CD safety consumption

This is especially important for a deployment-confidence service, because a stale or misleading decision service can be more dangerous than no decision service at all.

The system must therefore be able to tell consumers not only:

- “I am running”

but also:

- “I am ready”
- “I am fresh”
- “I am degraded”
- “I should not be trusted right now”

That is the real value of separating liveness, readiness, and health semantics.


## Grafana Dashboard

The Grafana dashboard is the **human-facing operational view** of `deploy-confidence-service`.

Its purpose is not to recompute deployment confidence. That work is already done by the service itself. Instead, the dashboard visualizes the **stored decision outputs** from PostgreSQL so operators can understand:

- the current deployment confidence
- whether deployment is allowed
- what is reducing confidence
- how confidence is changing over time
- whether the service is producing fresh results

This distinction is important.

For this project:
- **Prometheus** provides raw observability signals
- **deploy-confidence-service** computes the deployment decision
- **PostgreSQL** stores the decision history
- **Grafana** visualizes the decision and its explanation

The dashboard is therefore the human explanation layer of the system.

---

## Why the dashboard exists

A machine-readable API is necessary for CI/CD, but operators still need a fast visual way to understand what the service is doing.

The dashboard exists to answer questions like:

- Can we deploy right now?
- What is the current confidence score?
- What status did the service assign?
- Which component is currently reducing confidence?
- Is confidence stable or getting worse?
- Are decision updates still fresh?

This makes the dashboard useful for:
- platform engineers
- SREs
- incident review
- rollout planning
- release discussions
- demonstrations of the project’s value

---

## Dashboard data source

The dashboard uses **PostgreSQL** as its primary data source.

This is intentional.

Grafana does **not** compute the score from raw Prometheus metrics for this dashboard. Instead, it reads the final outputs already produced and stored by the service.

This gives several advantages:

- the dashboard shows the actual deployment decision used by the system
- historical decision data is easy to query
- component breakdowns are already stored
- no logic needs to be duplicated in Grafana
- dashboard values remain aligned with API output

This is one of the strongest parts of the overall architecture.

---

## Dashboard purpose

The dashboard has four major purposes:

### 1. Show the current decision
Operators should be able to tell, in a few seconds:
- the latest score
- deployment status
- whether deployment is allowed
- when the score was last updated

### 2. Explain the decision
Operators should be able to see:
- which component scores are low
- which components are healthy
- what is dragging confidence down
- why the latest result looks the way it does

### 3. Show history and trend
Operators should be able to tell:
- whether confidence is stable
- whether the service has recently degraded
- whether the same component keeps recurring as a risk
- whether deployment safety is improving or worsening over time

### 4. Build trust in the service
The dashboard should make the system inspectable.

It should help answer:
- does the dashboard match the API?
- does the score change over time?
- are score updates still fresh?
- is the service behaving like a real decision engine?

---

## Dashboard structure

The dashboard is organized around the deployment decision lifecycle.

A strong structure for this project includes the following logical sections:

1. **Current deployment decision**
2. **Confidence trend and freshness**
3. **Latest component breakdown**
4. **Component trends over time**
5. **Recent decision history**

This structure is intentionally decision-focused rather than infrastructure-focused.

The goal is not to replicate a generic Kubernetes dashboard.  
The goal is to visualize the deployment-confidence model itself.

---

## Row 1 — Current Deployment Decision

This is the most important row in the dashboard.

It should answer, immediately:

- What is the current confidence score?
- What is the current deployment status?
- Is deployment currently allowed?
- When was the decision last updated?
- What is the latest decision summary?

Typical panels in this row include:

### Current Confidence Score
Shows the latest final score as a single value.

This is the fastest way to understand the current deployment-confidence level.

### Current Deployment Status
Shows the current decision state:
- `DEPLOY`
- `CAUTION`
- `HOLD`

This is the operational classification of the latest score.

### Deploy Allowed
Shows whether the service currently permits deployment according to its own decision output.

This is especially useful because CI/CD pipelines also consume this idea in machine-readable form.

### Last Successful Update
Shows how recently the latest score run was generated.

This is important because a score is only trustworthy if it is still fresh.

### Latest Summary
Shows the short explanation generated by the service for the latest run.

This gives the operator a fast human-readable interpretation of the current state.

---

## Row 2 — Confidence Trend and Freshness

This row explains how deployment confidence behaves over time.

It answers:

- Is the score stable?
- Has confidence degraded recently?
- Are score runs occurring regularly?
- Is the service still updating often enough?

Typical panels in this row include:

### Confidence Score Over Time
Shows the final deployment-confidence score as a time series.

This is one of the most important panels because it turns the service from a point-in-time decision into a trend-aware operational signal.

### Deployment Status Timeline or History
Shows how the status has changed over time.

Depending on the data, this can be visualized as:
- a state timeline
- a recent-decision table

This helps operators see whether the environment has recently moved between `DEPLOY`, `CAUTION`, and `HOLD`.

### Score Runs in Last Hour
Shows whether the scheduler is continuing to generate fresh score runs.

This helps validate freshness operationally.

### Average Confidence Score
Shows the average deployment confidence over a recent time window such as the last hour.

This gives a more stable short-term trust signal than a single latest score.

---

## Row 3 — Latest Component Breakdown

This row explains **why** the latest score looks the way it does.

It is one of the most valuable sections in the entire dashboard.

It answers:

- Which component is currently weakest?
- Which component is strongest?
- What part of the platform is dragging confidence down?

Typical panels in this row include:

### Latest Component Scores
Shows the latest score for each scoring component, typically as a bar gauge.

This is a fast visual explanation of the latest decision.

For example, if:
- image pull health is low
- startup latency is moderate
- everything else is healthy

then the operator can immediately identify the likely reason for reduced deployment confidence.

### Latest Component Weights
Shows the configured scoring weights alongside component scores.

This is useful for understanding not just what is weak, but what has the most influence on the final decision.

### Top Risk Components
Shows the lowest-scoring components in the latest run, often along with their explanation text.

This is one of the strongest operator panels because it makes the latest risk drivers explicit.

---

## Row 4 — Component Trends Over Time

This row helps answer whether a particular component is a recurring problem.

It answers:

- Has image pull health been unstable repeatedly?
- Is node headroom drifting down over time?
- Is one signal consistently reducing deployment confidence?

Typical panels in this row include:

### Component Scores Over Time
Shows a trend line for each score component across multiple score runs.

This helps operators identify:
- recurring weakness
- long-term drift
- stable vs unstable components

### Lowest Component Score Trend
Shows the worst component score from each run over time.

This is a useful condensed risk panel because it surfaces how weak the weakest signal has been recently.

---

## Row 5 — Recent Decision History

This row acts as an audit and troubleshooting view.

It answers:

- What were the most recent deployment decisions?
- What score was recorded at each time?
- What summary was stored with those decisions?

Typical panels include:

### Recent Score Runs
A table showing:
- calculation time
- total score
- status
- deploy allowed
- threshold
- summary

This is one of the best panels for operator trust because it exposes the historical decision trail directly.

---

## How to read the dashboard

A good way to interpret the dashboard is:

### First
Look at the **Current Deployment Decision** row.

This tells you:
- the current score
- whether the system is in `DEPLOY`, `CAUTION`, or `HOLD`
- whether deployment is allowed
- whether the score is recent

### Second
Look at the **Latest Component Breakdown** row.

This tells you:
- what is actually reducing confidence
- which component needs attention first

### Third
Look at the **Confidence Trend** row.

This tells you:
- whether the latest result is an isolated fluctuation
- or part of a broader degrading pattern

### Fourth
Look at the **Recent Decision History** row.

This tells you:
- whether recent decisions have been stable
- whether the service has changed state over time
- whether a blocked deployment decision was part of an ongoing pattern

---

## Threshold semantics in the dashboard

The dashboard should align visually with the score model.

For score-based panels, the thresholds should generally be interpreted as:

- **0–69.99** → red / low confidence
- **70–84.99** → yellow / caution
- **85–100** → green / strong confidence

This keeps the visual language aligned with the service’s own interpretation model.

For status-based panels, use explicit value mappings:

- `DEPLOY` → green
- `CAUTION` → yellow
- `HOLD` → red

This is especially useful for state timelines and status summary panels.

---

## Why the dashboard is important to the project

The dashboard makes the project operationally complete.

Without Grafana, the service would still be technically strong because it exposes APIs and stores history.

But with Grafana, the project becomes easier to:
- operate
- demonstrate
- explain
- trust
- inspect in real time

This is especially important for platform engineering and SRE use cases, where human visibility and decision transparency matter as much as machine-readability.

---

## How the dashboard relates to the API

The dashboard and API are complementary.

### The API is for:
- CI/CD systems
- automation
- probes
- scripts
- programmatic consumption

### The dashboard is for:
- operators
- platform engineers
- troubleshooting
- decision review
- historical analysis

The dashboard should reflect the same truth as the API, not a different one.

That is why both the API and the dashboard should ultimately be backed by the same persisted score history.

---

## Dashboard screenshots

Include screenshots of the dashboard in this section of the README.

Recommended screenshots include:

- current deployment decision row
- confidence trend row
- latest component breakdown row
- recent decision history table

Suggested placeholders:


![Deployment Confidence Overview](img/deployment-confidence-overview.png)
![Latest Component Breakdown](img/latest-component-breakdown.png)
![Recent Deployment Decisions](img/recent-deployment-decisions.png)

### Why this dashboard is different from a generic cluster dashboard

This dashboard is not meant to replace Kubernetes dashboards or raw Prometheus dashboards.

Its role is different.

A generic cluster dashboard answers:

- what are CPU and memory doing?
- are pods restarting?
- how healthy is the cluster?

This dashboard answers:

- should we trust this platform enough to deploy right now?
- what is reducing deployment confidence?
- how has deployment trust changed over time?

That is why the dashboard belongs to the decision layer of the architecture.

It is visualizing deployment-confidence outcomes, not raw infrastructure telemetry.

### Dashboard value summary

The Grafana dashboard adds value in three ways:

### Human visibility

It lets operators understand the latest decision at a glance.

### Explainability

It shows which components are affecting deployment confidence and why.

### Historical trust

It allows teams to inspect how deployment confidence has changed over time and whether release conditions have been stable or risky.


## CI/CD Integration
![img](img/CICD-integration.png)

One of the most important outcomes of `deploy-confidence-service` is that it can be used not only for monitoring and visibility, but also for **deployment control**.

This is where the project moves beyond dashboards and APIs and becomes a real platform engineering component.

The service can be integrated into CI/CD in two different but related ways:

1. **as a service that has its own deployment pipeline**
2. **as a deployment gate that controls the rollout of other applications**

Both are important.

The first proves the service itself can be built, packaged, deployed, and verified like a real platform workload.

The second proves the service can influence release behavior and block risky deployments before rollout.

---

## Why CI/CD integration matters

Without CI/CD integration, the service is still useful:
- it computes confidence
- it stores history
- it exposes APIs
- it visualizes decisions in Grafana

But with CI/CD integration, it becomes operationally powerful.

It can answer the most important question in delivery:

**Should this deployment continue right now?**

This matters because many teams still do this manually by checking dashboards and making a judgment call.

`deploy-confidence-service` allows that decision to become:
- measurable
- repeatable
- explainable
- automatable

That is why CI/CD integration is one of the strongest parts of the project.

---

## Two pipeline roles in this project

The project includes two distinct CI/CD roles.

### 1. Service deployment pipeline

This pipeline is responsible for deploying the `deploy-confidence-service` itself.

Its job is to:
- run tests
- build the image
- push the image to a registry
- deploy the service into Kubernetes
- verify rollout
- verify service endpoints

This is the platform-service delivery pipeline.

It proves the service can be maintained and released like a real Kubernetes-native workload.

### 2. Consumer application gate pipeline

This pipeline is responsible for using the service as a **pre-deploy confidence gate** before another application is deployed.

Its job is to:
- verify the service is ready and healthy
- retrieve the current confidence result
- evaluate that result against deployment policy
- allow or block deployment based on the environment

This is the release-control pipeline.

It proves the service can influence real deployment decisions.

---

## Service deployment pipeline

The service deployment pipeline exists so that `deploy-confidence-service` can be built and released as a production-style component.

### What it does

A typical service deployment pipeline should perform the following stages:

1. **run tests**
2. **build Docker image**
3. **push image to registry**
4. **update Kubernetes deployment**
5. **wait for rollout**
6. **verify `/live`, `/ready`, and `/health`**

### Why this matters

This proves that the service is not just a local development project. It is something that can be:
- versioned
- packaged
- deployed
- verified
- operated

### What this pipeline demonstrates

This pipeline demonstrates:
- packaging discipline
- Kubernetes delivery workflow
- rollout verification
- API-based post-deploy validation
- production-style release flow for the service itself

It also makes the project easier to explain because it shows that the service is self-contained and deployable.

---

## Consumer application gate pipeline

This is the more strategically important pipeline from a platform and SRE point of view.

It is the pipeline that uses `deploy-confidence-service` as a **pre-deploy decision engine**.

### What it does

Before deploying a consumer application, the pipeline:

1. checks whether the confidence service is ready
2. checks whether its health status is trustworthy
3. verifies score freshness
4. retrieves the current deployment score
5. retrieves detailed explanation data if needed
6. compares the score against policy thresholds
7. blocks or allows deployment

### Why this matters

This is the step that turns the project from observability into release control.

Instead of saying:
- “here is the score”

the platform can now say:
- “deployment is blocked because confidence is below policy”

That is a much stronger operational outcome.

---

## CI/CD gate flow

The intended gate flow looks like this:

```text
Consumer pipeline starts
   ↓
Check deploy-confidence-service /ready
   ↓
Check deploy-confidence-service /health
   ↓
Ensure health status is ok and score is fresh
   ↓
Query /score
   ↓
Compare score to environment threshold
   ↓
Optionally query /details for explanation
   ↓
Pass deployment or block deployment
```
> This sequence is important because deployment should not rely only on the score. It should first verify that the confidence service itself is healthy and fresh enough to trust.

### Environment-based policy

A deployment-confidence score should not necessarily be interpreted the same way in every environment.

A development environment usually tolerates more risk than production.

That is why the consumer gate pipeline supports environment-based thresholds.

A strong initial policy model is:

- `dev → threshold 60`
- `staging → threshold 75`
- `prod → threshold 85`

This allows the same service to support different rollout behaviors depending on environment criticality.

### Why this is useful

It makes the confidence service practical for real delivery workflows because:

- development can move faster
- staging can be more cautious
- production can be stricter

This reflects how real release governance works.

### Decision enforcement model

The consumer pipeline can use several decision signals together:

- `score`
- `status`
- `deploy_allowed`
- `score_fresh`
- `health status`

A strong baseline policy is:

- fail if `/ready` fails
- fail if `/health` is not ok
- fail if `score_fresh` is false
- fail if `deploy_allowed` is false
- fail if `score < threshold`
- fail if `status == HOLD`

A stricter production policy can also include:

- block production if status == CAUTION

This creates an environment-aware rollout trust model.

### Why `/details` matters in CI/CD

If the gate blocks deployment, simply returning “score below threshold” is not enough.

Pipelines should be able to explain why the deployment was blocked.

That is where `/details` becomes valuable.

A pipeline can query `/details` and extract:

- lowest scoring components
- explanation text
- raw risk context

This makes CI/CD output more useful because it can surface messages such as:

- image pull health is reducing rollout confidence
- startup latency is elevated
- dependency checks failed
- recent restart pressure is too high

This is one of the strongest design choices in the project because it makes failed gates explainable.

### Gate evidence and auditability

A production-style gate should preserve evidence when it evaluates or blocks a deployment.

A strong CI/CD pattern is to retain:

- readiness response
- health response
- score response
- details response

These can be saved as:

- artifacts
- logs
- step summaries
- release evidence

This matters because blocked deployments often lead to questions such as:

- what score was returned?
- what status was assigned?
- what were the top risk components?
- was the block justified?

Keeping gate evidence makes the decision auditable.

### Service health before score trust

One of the most important CI/CD design principles in this project is:

Do not trust a deployment score from an unhealthy or stale service.

That is why the pipeline should not call /score in isolation.

It should first validate:

- readiness
- health
- score freshness

This is a critical design point because a stale decision service can mislead deployment pipelines.

> The project therefore treats the deployment-confidence service itself as a dependency that must be trustworthy before its output is consumed.

### Relationship between dashboard and pipeline

The Grafana dashboard and CI/CD pipeline serve different consumers but rely on the same decision model.

Grafana provides
- human-readable visibility
- trend analysis
- operator explanation
- historical inspection

CI/CD provides
- automated enforcement
- deployment blocking
- release policy consumption
- machine-readable decision control

This is important because the project is designed to support both:

- humans making platform judgments
- systems making release decisions

That combination is one of the strongest parts of the architecture.

### What CI/CD integration proves

By integrating the service into CI/CD, the project proves that it can do more than observe risk.

It can:

- evaluate deployment trust continuously
- expose that trust through API
- store its decision history
- explain its decisions
- influence rollout behavior automatically

That is a much stronger outcome than simply showing a dashboard.

### Typical consumer pipeline policy example

A consumer pipeline can implement policy like this:

### Dev
- allow deployment if score is at least `60`
### Staging
- allow deployment if score is at least `75`
### Prod
- allow deployment only if score is at least `85`
- optionally block on `CAUTION`
- always block on `HOLD`

This policy model is intentionally simple but realistic.

> It gives the project a strong production-style interpretation without making the implementation overly complex.

### Why this CI/CD model is valuable

This CI/CD model is valuable because it connects:

- observability
- platform trust
- deployment safety
- automation

Instead of relying on manual judgment each time, teams can now use a service that standardizes how deployment confidence is evaluated.

That gives several benefits:

- more consistent deployment policy
- reduced subjective decision-making
- explainable deployment blocks
- reusable rollout-safety logic
- clearer relationship between platform health and release control

### CI/CD integration summary

The project supports two complementary CI/CD roles:

Service deployment pipeline

This pipeline ensures the confidence service itself can be:

- tested
- built
- pushed
- deployed
- verified

### Consumer application gate pipeline

This pipeline ensures deployments can be:

- checked against platform confidence
- blocked if risk is too high
- explained through component-level detail

> Together, these make the project much stronger. 
> They show that deploy-confidence-service is not just a monitoring idea. 
> It is a deployment-decision system that can be delivered, operated, and consumed in real release workflows.


## Running Locally

This section explains how to run `deploy-confidence-service` in a local development environment.

The goal of local execution is to let you:
- start the API
- connect to PostgreSQL
- validate the scheduler
- inspect `/live`, `/ready`, `/health`, `/score`, and `/details`
- test changes before packaging or Kubernetes deployment

Local execution is especially useful when:
- developing collectors
- tuning the scoring model
- verifying persistence behavior
- validating health semantics
- testing API changes
- debugging the scheduler loop

---

## Prerequisites

Before running the service locally, make sure the following are available:

- Python `3.11+`
- `pip`
- a local or reachable PostgreSQL instance
- access to a Prometheus endpoint
- access to Kubernetes if you want live Kubernetes collection
- optional: `curl` for endpoint testing

If you want the service to use a real Kubernetes cluster during local development, you also need:
- a valid kubeconfig
- network access to the cluster
- access to Prometheus and the required dependencies

---

## Project structure expectation

Run the service from the project root, or clone my repo, file exist are:

- `app/`
- `tests/`
- `requirements.txt`
- `.env`
- `Dockerfile`
- `k8s/`

This ensures imports, config loading, and startup behavior work as expected.

---

## 1. Create and activate a virtual environment

Create a Python virtual environment:

```bash
mkdir -p ~/.venvs
python3 -m venv ~/.venvs/deploy-confidence-service
source ~/.venvs/deploy-confidence-service/bin/activate
cd /mnt/data/deploy-confidence-service
````


2. Install dependencies

Install the application dependencies:

```shell
pip install --upgrade pip
pip install -r requirements.txt
```

This installs the packages required for:

- FastAPI
- SQLAlchemy
- PostgreSQL connectivity
- APScheduler
- Kubernetes client
- Prometheus querying
- testing
- local execution

---

3. Configure environment variables

Create a `.env` file in the project root.

A typical local development example looks like this:

```shell
APP_NAME=deploy-confidence-service
APP_VERSION=0.1.0
APP_ENV=development
LOG_LEVEL=INFO

API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql+psycopg://deploy_confidence:change_me@localhost:5432/deploy_confidence
PROMETHEUS_URL=http://localhost:9090

CHECK_INTERVAL_SECONDS=120
DEPLOY_THRESHOLD=70

KUBERNETES_IN_CLUSTER=false
```
### Important notes
`DATABASE_URL`

This should point to a PostgreSQL instance you can reach locally.

`PROMETHEUS_URL`

This should point to a reachable Prometheus endpoint.

If Prometheus is running in Kubernetes, a common local development option is to port-forward it:

```shell
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090
```

Then you can use:

```shell
PROMETHEUS_URL=http://localhost:9090
```
`KUBERNETES_IN_CLUSTER`

For local development, this should normally be:

```shell
KUBERNETES_IN_CLUSTER=false
```

That tells the Kubernetes client to use your local kubeconfig rather than in-cluster service account credentials.

4. Prepare PostgreSQL

You need a PostgreSQL database before starting the app.

A simple local example using Docker:

```shell
docker run -d \
  --name deploy-confidence-postgres \
  -e POSTGRES_DB=deploy_confidence \
  -e POSTGRES_USER=deploy_confidence \
  -e POSTGRES_PASSWORD=change_me \
  -p 5432:5432 \
  postgres:16
```

This creates a local PostgreSQL instance exposed on port 5432.

Your `.env` should match the same credentials.

Verify PostgreSQL is reachable
```shell
docker exec -it deploy-confidence-postgres psql -U deploy_confidence -d deploy_confidence
```

If the connection works, PostgreSQL is ready for the service.

5. Ensure Prometheus is reachable

If Prometheus is running inside Kubernetes, port-forward it locally:

```shell
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090
```

Then test it:

```shell
curl http://localhost:9090/api/v1/status/buildinfo
```

If Prometheus is reachable, you should get a JSON response with version/build information.

If this step fails, the scheduler will start but score updates will fail because the Prometheus collector cannot connect.

6. Run the application

Start the service with Uvicorn:

```shell
uvicorn app.main:app --reload
```

This starts the FastAPI application locally and enables auto-reload for development.

On startup, the service should:

- initialize database tables
- run an immediate score update job
- start the scheduler
- begin serving the API on port 8000

Typical local URL:

```shell
http://127.0.0.1:8000

or

http://localhost:8000
```
7. What should happen on startup

A successful startup should include logs indicating:

- application startup
- database initialization
- first score update attempt
- scheduler startup

Expected operational behavior:

- tables are created if they do not exist
- one score run is attempted immediately
- the recurring scheduler begins
- new score runs continue on the configured interval

If Prometheus, PostgreSQL, and Kubernetes access are valid, the first score run should persist successfully.

8. Verify the API endpoints

After startup, verify the service endpoints.

Liveness
```shell
curl http://localhost:8000/live
```

Expected result:

- service responds with a minimal alive status

Readiness
```shell
curl http://localhost:8000/ready
```

Expected result:

- readiness succeeds only if DB is healthy, scheduler is running, and the score is fresh

Health
```shell
curl http://localhost:8000/health
```

Expected result:

- detailed health response showing:
  - database health
  - scheduler health
  - freshness
  - last successful score update
  - last error if present

Score
```shell
  curl http://localhost:8000/score
```

Expected result:

- latest deployment confidence score and summary

Details
```shell
curl http://localhost:8000/details
```

Expected result:

- latest deployment confidence score plus full component breakdown

9. What a healthy local run looks like

A healthy local run usually means:

- /live returns success
- /ready returns success
- /health returns status: ok
- /score returns the latest score
- /details returns component breakdown
- PostgreSQL tables are populated
- scheduler continues writing new score runs

A healthy /health example includes fields like:

- database_healthy: true
- scheduler_healthy: true
- score_fresh: true
- last_error: null

10. Verify persistence

You can inspect PostgreSQL directly to confirm the scheduler is writing results.

Connect to PostgreSQL:

```shell
docker exec -it deploy-confidence-postgres psql -U deploy_confidence -d deploy_confidence
```
Then inspect the tables:

```shell
SELECT count(*) FROM score_runs;
SELECT count(*) FROM score_components;
```

You should see:

- at least one row in score_runs
- multiple rows in score_components
- increasing counts as the scheduler continues to run

To inspect recent results:

```shell
SELECT
  calculated_at,
  total_score,
  status,
  deploy_allowed,
  summary
FROM score_runs
ORDER BY calculated_at DESC
LIMIT 10;
```
11. Run tests locally

Before or after starting the service, you can run the test suite:

```shell
pytest -q
```

Or run focused test groups:

```shell
pytest tests/test_normalization.py tests/test_scoring_engine.py tests/test_collectors.py -q
pytest tests/test_health_api.py tests/test_scheduler.py -q
```
This validates:

- normalization logic
- scoring engine behavior
- collectors
- health semantics
- scheduler behavior

12. Common local development patterns

### Pattern A — Fully local database, cluster-backed metrics

Use:

- local PostgreSQL container
- local Uvicorn
- Prometheus port-forward
- kubeconfig-based Kubernetes access

This is one of the most useful development patterns because it keeps the app local but uses live cluster data.

### Pattern B — Mostly mocked or test-driven development

Use:

- tests only
- mocked collectors
- no running cluster dependency

This is useful when working on:

- scoring logic
- endpoint behavior
- service semantics
- persistence layer

### Pattern C — Full local validation before container build

Use:

- local PostgreSQL
- local Prometheus access
- local Uvicorn
- endpoint verification
- test suite

This is useful before Docker packaging or Kubernetes deployment.

### 13. Troubleshooting local runs
Problem: /score returns no result

Possible causes:

- scheduler has not completed a successful score update
- Prometheus is unreachable
- database writes failed
- initial score update failed on startup

Check:

- app logs
- /health
- PostgreSQL rows

Problem: /health shows degraded

Possible causes:

- Prometheus query failed
- score is stale
- database check failed
- scheduler is not running

Check:

- last_error
- score_fresh
- Prometheus connectivity
- database connectivity

Problem: Prometheus connection refused

This usually means:

- PROMETHEUS_URL is wrong
- Prometheus is not running
- port-forward is missing
- local URL does not match real endpoint

Test directly:

```shell
curl http://localhost:9090/api/v1/status/buildinfo
```
Problem: Kubernetes collector cannot load config

This usually means:

- KUBERNETES_IN_CLUSTER is incorrect
- kubeconfig is not available locally
- cluster access is missing

For local development, ensure:

```shell
KUBERNETES_IN_CLUSTER=false
```

and verify your kubeconfig works:
```shell

kubectl get nodes
```
Problem: /ready fails while /live works

This usually means:

- the process is alive
- but the service is not operationally ready

Likely reasons:

- database unhealthy
- scheduler not started
- score is stale

That is expected behavior based on the service design.

14. Local run summary

A successful local development setup should allow you to:

- start the service with Uvicorn
- connect to PostgreSQL
- access Prometheus
- use kubeconfig-based Kubernetes access
- observe scheduler behavior
- query all service endpoints
- inspect stored score history
- run tests

This local workflow is the foundation for:

- feature development
- score tuning
- endpoint debugging
- scheduler debugging
- pre-container validation

It is the fastest way to validate changes before moving to Docker or Kubernetes deployment.



## Docker and Container Usage

Containerizing `deploy-confidence-service` makes the project easier to:
- run consistently
- package for Kubernetes
- validate outside the local Python environment
- deploy through CI/CD
- share as a reproducible platform service

This section explains how Docker fits into the project, how to build and run the image, what environment configuration is required, and what to watch for when running the service inside a container.

---

## Why Docker is used

Docker is important in this project for several reasons.

### 1. Consistent runtime
A container gives the service a predictable runtime environment regardless of the local machine configuration.

### 2. Kubernetes deployment
The service is designed to run inside Kubernetes, so container packaging is part of the normal deployment model.

### 3. CI/CD delivery
The service deployment pipeline builds and pushes a container image before rollout.

### 4. Security and hardening
The project uses a hardened Dockerfile so the service runs more like a production-style workload.

This makes Docker part of the actual delivery path, not just a convenience tool.

---

## Dockerfile goals

The Dockerfile in this project is designed to:

- use a lightweight Python base image
- install only the required dependencies
- run the FastAPI service directly
- avoid unnecessary build artifacts
- support a non-root execution model
- align with Kubernetes deployment security settings

This matters because the service is intended to run in a real platform environment, not just as a local development script.

---

## Typical Dockerfile structure

A production-style Dockerfile for this project should:

1. start from a slim Python base image
2. disable unnecessary Python bytecode generation
3. install requirements
4. copy the application code
5. switch to a non-root user
6. run Uvicorn as the container entry point

A typical implementation looks like this:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -u 10001 -r -s /usr/sbin/nologin appuser

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

USER 10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


- This aligns well with the hardened Kubernetes deployment model.

`.dockerignore`

A `.dockerignore` file is strongly recommended to keep the image clean and small.

Typical entries include:

```gitignore
.git
.gitignore
.venv
venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.mypy_cache
.coverage
htmlcov
dist
build
*.egg-info
.env
.idea
.vscode
```

This prevents:

- local virtual environments
- caches
- editor files
- test artifacts
- local secrets

from being copied into the image.

Build the image

From the project root, build the image with:

```shell
docker build -t deploy-confidence-service:latest .
```

This creates a local image named:

```shell
deploy-confidence-service:latest
```

If you are preparing for registry push, you can also tag it directly:
```shell
# It is recommended to use an environment variable for security
export CR_PAT=YOUR_PERSONAL_ACCESS_TOKEN
echo $CR_PAT | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
docker build -t ghcr.io/<your-user>/deploy-confidence-service:0.1.0 .
docker push ghcr.io/<your-user>/deploy-confidence-service:0.1.0
```

Run the container locally

A basic local run looks like this:

```shell
docker run --rm -p 8000:8000 --env-file .env deploy-confidence-service:latest
```

This tells Docker to:

- expose the API on port 8000
- load environment variables from .env
- remove the container when it exits

Once running, the API should be reachable at:
```shell
http://localhost:8000
```

Important networking note

When the application runs inside a container, localhost no longer refers to your host machine. It refers to the container itself.

This is one of the most important Docker concepts in this project.

Example problem

If your `.env` contains:

```shell
DATABASE_URL=postgresql+psycopg://deploy_confidence:change_me@localhost:5432/deploy_confidence
PROMETHEUS_URL=http://localhost:9090
```

that will only work if:

- PostgreSQL is running inside the same container
- Prometheus is running inside the same container

That is not the case here.

So inside Docker, `localhost` usually becomes the wrong value for external dependencies.

### Local container runtime options

There are several ways to make dependencies reachable from the container.

### Option 1 — Use host networking

On Linux, a simple local testing approach is:

```shell
docker run --rm --network host --env-file .env deploy-confidence-service:latest
```

This allows the container to use the host’s network directly.

This is often the easiest way to test if:

- PostgreSQL is running on the host
- Prometheus is port-forwarded on the host
- you want quick local validation

### Option 2 — Use explicit hostnames

If PostgreSQL and Prometheus are running in other containers or reachable through known hostnames, update the environment values to use those names instead of localhost.

### Option 3 — Use Kubernetes-native deployment

This is the intended long-term runtime model for the project.

In Kubernetes:

- PostgreSQL has a service DNS name
- Prometheus has a service DNS name
- the service runs in-cluster
- Kubernetes API access uses service account credentials

This is the cleanest production-style setup.

Example local container configuration

A local Docker run may need environment values like:

```dotenv
APP_NAME=deploy-confidence-service
APP_VERSION=0.1.0
APP_ENV=development
LOG_LEVEL=INFO

API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql+psycopg://deploy_confidence:change_me@host.docker.internal:5432/deploy_confidence
PROMETHEUS_URL=http://host.docker.internal:9090

CHECK_INTERVAL_SECONDS=120
DEPLOY_THRESHOLD=70

KUBERNETES_IN_CLUSTER=false
```
Important note on `host.docker.internal`

This works well on:

- Docker Desktop environments
- some host/container setups

On Linux, host networking is often simpler than relying on `host.docker.internal`.

Verify the running container

Once the container is running, validate the endpoints:

###Liveness
```shell
curl http://localhost:8000/live
```
### Readiness
```shell
curl http://localhost:8000/ready
```
### Health
```shell
curl http://localhost:8000/health
```
### Score
```shell
curl http://localhost:8000/score
```
### Details
```shell
curl http://localhost:8000/details
```

A healthy containerized run should behave the same way as a local Uvicorn run, assuming all dependencies are reachable.

### What a healthy container run should do

A successful container startup should:

- initialize database tables
- run the initial score update
- start the scheduler
- expose the FastAPI service
- produce a healthy `/live`
- produce a meaningful `/ready`
- expose current score through `/score`
- expose full breakdown through `/details`

If PostgreSQL or Prometheus are unreachable, the container may still be alive but readiness and score behavior will reflect the dependency problem.

That is expected and consistent with the service design.

### Container logs

To inspect runtime behavior, check the container logs:

```shell
docker logs <container-name>
```

Useful signals in the logs include:

- application startup
- database initialization
- immediate score update attempt
- scheduler startup
- collector failures
- Prometheus connectivity errors
- score update completion

Logs are especially useful for debugging:

- readiness failures
- score freshness issues
- initial startup problems
- Running PostgreSQL separately with Docker

For local container-based testing, you can also run PostgreSQL as a separate container.

Example:

```shell
docker run -d \
  --name deploy-confidence-postgres \
  -e POSTGRES_DB=deploy_confidence \
  -e POSTGRES_USER=deploy_confidence \
  -e POSTGRES_PASSWORD=change_me \
  -p 5432:5432 \
  postgres:16
```

Then adjust `DATABASE_URL` accordingly.

If using Docker networking between containers, place both containers on the same Docker network and use the PostgreSQL container name as the hostname.

### Registry tagging and push

For Kubernetes deployment and CI/CD, the image usually needs to be pushed to a registry.

Example with GitHub Container Registry:

```shell
Tag
docker tag deploy-confidence-service:latest ghcr.io/<your-user>/deploy-confidence-service:0.1.0
Login
echo "$GHCR_TOKEN" | docker login ghcr.io -u <your-user> --password-stdin
Push
docker push ghcr.io/<your-user>/deploy-confidence-service:0.1.0
```

This makes the image available for the Kubernetes deployment and CI/CD workflow.

### Relationship to Kubernetes deployment

The container is the runtime unit that Kubernetes deploys.

That means Docker is not only for local testing. It is also the packaging format for:

- Kubernetes Deployment manifests
- CI/CD build-and-push stages
- service rollout verification

The Kubernetes deployment then adds:

- environment injection
- service account
- RBAC
- probes
- cluster DNS
- in-cluster Prometheus
- in-cluster PostgreSQL

So Docker and Kubernetes are closely linked in the final runtime model.

### Security and hardening considerations

The container should align with the project’s hardened deployment design.

Important container-level security properties include:

- non-root execution
- minimal base image
- no unnecessary packages
- clean dependency installation
- no embedded secrets in the image
- configuration injected through environment variables

This is important because the project is positioned as a production-style platform service.

### When to use Docker in this project

Use Docker when you want to:

- validate the application outside your local Python environment
- test container behavior before Kubernetes deployment
- build the image that CI/CD will push
- reproduce the service environment more consistently
- package the app for registry-based deployment

Use direct local Uvicorn execution when you want:

- fastest iteration
- easiest debugging
- simplest local testing

Both are useful. Docker is the more deployment-oriented path.

Docker usage summary

Docker gives the project a reproducible runtime form that supports:

- local validation
- CI/CD build-and-push
- Kubernetes deployment
- hardened service packaging

It is an essential part of turning deploy-confidence-service from a local development project into a real deployable platform component.

The recommended flow is:

- validate locally
- build container
- test container behavior
- push image to registry
- deploy to Kubernetes

> That makes Docker a central part of both development and delivery for the project.




## Kubernetes Deployment

`deploy-confidence-service` is designed to run as a **Kubernetes-native platform component**.

Running it in-cluster is the intended deployment model because it gives the service direct access to the systems it depends on:

- Kubernetes API
- Prometheus
- PostgreSQL
- service account credentials
- in-cluster service discovery
- Kubernetes probes and rollout semantics

This section explains how the service is deployed into Kubernetes, what resources it needs, how PostgreSQL is provided, how configuration is injected, how health probes are used, and how to verify a successful rollout.

---

## Why Kubernetes is the target runtime

This service is meant to evaluate the deployment trust of a Kubernetes environment, so running it inside the same environment is the cleanest and most realistic architecture.

This deployment model provides several advantages:

- the service can use in-cluster Kubernetes authentication
- Prometheus can be reached by service DNS
- PostgreSQL can be reached by service DNS
- readiness and liveness can be enforced natively
- rollout and restart behavior align with platform operations
- CI/CD consumers inside the environment can query it directly

This makes the service part of the platform, not an external observer.

---

## Kubernetes resources used

A typical deployment includes the following Kubernetes resources:

- **Namespace**
- **ServiceAccount**
- **RBAC**
- **ConfigMap**
- **Secret**
- **PostgreSQL Secret**
- **PersistentVolumeClaim**
- **PostgreSQL workload**
- **PostgreSQL Service**
- **Deploy-Confidence-Service Deployment**
- **Deploy-Confidence-Service Service**

Each resource has a clear purpose in the overall runtime model.

---

## 1. Namespace

The service is deployed into its own namespace.

Typical namespace name:

```text
deploy-confidence
```


### Why this matters

Using a dedicated namespace keeps the service isolated from unrelated workloads and makes it easier to manage:

- service resources
- secrets
- configmaps
- PostgreSQL
- RBAC
- rollout inspection

Example manifest
```shell
apiVersion: v1
kind: Namespace
metadata:
  name: deploy-confidence
```
### 2. Service account

The application runs under its own Kubernetes service account.

Typical name:

```shell
deploy-confidence-sa
```
### Why this matters

The service account allows the application to authenticate to the Kubernetes API from inside the cluster.

This is required because the Kubernetes collector needs to query resources such as:

- pods
- events
- namespaces

Example manifest
```shell
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deploy-confidence-sa
  namespace: deploy-confidence
```
### 3. RBAC

The service needs read-only access to selected Kubernetes resources.

Typical cluster-wide access is used for:

- pods
- events
- namespaces

### Why this matters

The service needs to read deployment-related Kubernetes data, but it should not be able to modify resources.

This is why RBAC should remain read-only and limited to the resources the collectors actually need.

### Example RBAC
```shell
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: deploy-confidence-cluster-reader
rules:
  - apiGroups: [""]
    resources: ["pods", "events", "namespaces"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: deploy-confidence-cluster-reader-binding
subjects:
  - kind: ServiceAccount
    name: deploy-confidence-sa
    namespace: deploy-confidence
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: deploy-confidence-cluster-reader
```
### Why this design is important

This allows the service to inspect cluster state without granting write access.

That is a strong production-style security decision.

---

### 4. ConfigMap

Non-sensitive runtime configuration is injected through a ConfigMap.

Typical values include:

- app name
- version
- environment
- log level
- API host and port
- Prometheus URL
- scheduler interval
- threshold
- KUBERNETES_IN_CLUSTER=true

### Why this matters

A ConfigMap keeps operational settings separate from the image and allows them to be changed without rebuilding the application.

Example values
```shell
apiVersion: v1
kind: ConfigMap
metadata:
  name: deploy-confidence-config
  namespace: deploy-confidence
data:
  APP_NAME: "deploy-confidence-service"
  APP_VERSION: "0.1.0"
  APP_ENV: "production"
  LOG_LEVEL: "INFO"

  API_HOST: "0.0.0.0"
  API_PORT: "8000"

  PROMETHEUS_URL: "http://kps-kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090"

  CHECK_INTERVAL_SECONDS: "120"
  DEPLOY_THRESHOLD: "70"

  KUBERNETES_IN_CLUSTER: "true"
```
### Why the Prometheus URL is important

Inside Kubernetes, the service should use the Prometheus service DNS name rather than localhost.

This is one of the key differences between local development and in-cluster runtime.

### 5. Application secret

Sensitive application configuration is injected through a Secret.

The most important value is:

- DATABASE_URL

### Why this matters

Database credentials and connection strings should not be stored directly in:

- source code
- ConfigMaps
- container images

Secrets keep runtime-sensitive values separate and more manageable.

Example secret
```shell
apiVersion: v1
kind: Secret
metadata:
  name: deploy-confidence-secret
  namespace: deploy-confidence
type: Opaque
stringData:
  DATABASE_URL: "postgresql+psycopg://deploy_confidence:change_me@deploy-confidence-postgres.deploy-confidence.svc.cluster.local:5432/deploy_confidence"
```
### 6. In-cluster PostgreSQL

The service requires PostgreSQL because score history and component breakdowns are persisted there.

In Kubernetes, PostgreSQL is deployed as an in-cluster stateful dependency.

Typical resources include:

- PostgreSQL Secret
- PersistentVolumeClaim
- PostgreSQL workload
- PostgreSQL Service

### Why PostgreSQL is included in-cluster

Running PostgreSQL in-cluster makes the project self-contained and easier to demonstrate.

It also allows:

- simple service DNS usage
- persistent score history
- dashboard connectivity
- cleaner environment packaging

### 7. PostgreSQL Secret

A dedicated PostgreSQL Secret is used for:

- database name
- username
- password

Example manifest
```shell
apiVersion: v1
kind: Secret
metadata:
  name: deploy-confidence-postgres-secret
  namespace: deploy-confidence
type: Opaque
stringData:
  POSTGRES_DB: deploy_confidence
  POSTGRES_USER: deploy_confidence
  POSTGRES_PASSWORD: change_me
```

This secret is separate from the application secret to keep responsibilities clean.

### 8. Persistent storage

PostgreSQL requires persistent storage.

A PersistentVolumeClaim is used for its data directory.

Why this matters

Without persistent storage:

- score history would be lost on restart
- Grafana history would disappear
- the service would lose auditability
- the database would not behave like a real operational dependency

Example PVC
```shell
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: deploy-confidence-postgres-pvc
  namespace: deploy-confidence
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: longhorn-retain
  resources:
    requests:
      storage: 5Gi
```
### Why storage class pinning matters

Pinning the storage class makes persistence intentional and reproducible.

This is especially important in homelab and production-style environments where multiple storage classes may exist.

### 9. PostgreSQL workload

PostgreSQL is deployed as a Kubernetes-managed workload with a persistent volume and health probes.

A hardened setup should use:

- the PostgreSQL Secret
- persistent volume mount
- readiness probe
- liveness probe
- resource requests and limits

Example workload structure

It should:

- mount /var/lib/postgresql/data
- read credentials from Secret
- expose port 5432
- use pg_isready for health checks

### Why health probes matter here

The main service depends on PostgreSQL to become ready.

If PostgreSQL is unavailable:

- the service cannot persist score history
- readiness should fail
- health should reflect the issue

This makes PostgreSQL a real dependency, not an optional extra.

### 10. PostgreSQL Service

A Kubernetes Service exposes PostgreSQL inside the namespace.

Typical name:

```shell
deploy-confidence-postgres
```
### Why this matters

This allows the application to reach PostgreSQL via stable in-cluster DNS:

```shell
deploy-confidence-postgres.deploy-confidence.svc.cluster.local:5432
```

This is how the DATABASE_URL in the application Secret should be constructed.

### 11. Deploy-Confidence-Service Deployment

The main application is deployed as a Kubernetes Deployment.

It includes:

- container image
- service account
- ConfigMap and Secret injection
- hardened security context
- probes
- resource requests and limits

### Why Deployment is used

The application itself is stateless in runtime behavior, even though it depends on PostgreSQL for history.

That makes Deployment the correct workload type for the service.

Example key deployment properties

The Deployment should include:

- serviceAccountName: deploy-confidence-sa
- env values from ConfigMap and Secret
- non-root execution
- seccomp profile
- dropped Linux capabilities
- startup probe
- liveness probe
- readiness probe

This makes the pod closer to a production-style application workload.

### 12. Security context and hardening

The Deployment should be hardened with settings such as:

- runAsNonRoot: true
- runAsUser: 10001
- allowPrivilegeEscalation: false
- dropped capabilities
- seccompProfile: RuntimeDefault

### Why this matters

> These settings reduce container risk and align the deployment with stronger platform security practices.
> This is important because the service is meant to look and behave like a real platform component, not just a lab demo.

### 13. Probe design

The deployment should use three probe types:

- startupProbe
- livenessProbe
- readinessProbe

#### Startup probe

Uses:

- `/live`

Purpose:

- allow slower initialization without premature restarts
- give database init and scheduler startup time to complete

### Liveness probe

Uses:

- `/live`

Purpose:

- restart the container only when the process is unhealthy

### Readiness probe

Uses:

- `/ready`

Purpose:

- ensure traffic is routed only when:
- database is healthy
- scheduler is running
- score is fresh

### Why this split matters

This is a stronger design than pointing all probes at the same endpoint.

It reflects the fact that:

- process liveness
- service readiness
- operational health

are not the same thing.

### 14. Service for the application

A ClusterIP Service exposes the FastAPI application inside the cluster.

Typical name:

```shell
deploy-confidence-service
```

This allows in-cluster consumers to access the application by DNS.

Examples:

- Grafana if needed
- internal scripts
- CI/CD runners with cluster network access
- other in-cluster consumers

### Why this matters

The CI/CD gate and in-cluster verification workflows depend on the service having a stable internal address.

### 15. Typical deployment order

A reliable apply order is:

- namespace
- service account
- RBAC
- PostgreSQL Secret
- PVC
- PostgreSQL workload
- PostgreSQL Service
- ConfigMap
- application Secret
- Deploy-Confidence-Service Deployment
- application Service

This order helps ensure dependencies exist before the application starts.

### 16. Example apply commands
```shell
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/role.yaml
kubectl apply -f k8s/rolebinding.yaml

kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/postgres-service.yaml

kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```
### 17. Rollout verification

After deployment, verify that all resources are healthy.

Check pods
```shell
kubectl get pods -n deploy-confidence
```

You should see:

- PostgreSQL pod
- Deploy-Confidence-Service pod

Both should become Running.

Check services
```shell
kubectl get svc -n deploy-confidence
```

You should see:

- PostgreSQL service
- application service

Check PVC
```shell
kubectl get pvc -n deploy-confidence
```

The PostgreSQL PVC should be Bound.

Check logs
Application logs
```shell
kubectl logs -n deploy-confidence deploy/deploy-confidence-service
```

You should see:

- startup logs
- DB initialization
- initial score update attempt
- scheduler startup

PostgreSQL logs
```shell
kubectl logs -n deploy-confidence <postgres-pod-name>
```

You should see normal PostgreSQL startup behavior.

### 18. Endpoint verification in-cluster

You can verify the application endpoints by port-forwarding the service:

```shell
kubectl -n deploy-confidence port-forward svc/deploy-confidence-service 8000:8000
```

Then locally test:

```shell
curl http://localhost:8000/live
curl http://localhost:8000/ready
curl http://localhost:8000/health
curl http://localhost:8000/score
curl http://localhost:8000/details
```
Expected healthy behavior

A healthy deployment should show:

- `/live` returns success
- `/ready` returns ready
- `/health` returns status: ok
- `/score` returns latest deployment confidence
- `/details` returns latest component breakdown

### 19. Common deployment issues
Problem: pod is alive but not ready

Possible causes:

- PostgreSQL is not reachable
- scheduler has not yet completed a successful score update
- score freshness is false
- Prometheus is unreachable from inside the cluster

Problem: score updates fail

Possible causes:

- wrong Prometheus service URL in ConfigMap
- RBAC issue prevents Kubernetes collector from reading resources
- database connection string is wrong
- PostgreSQL service is not healthy yet

Problem: `/health` shows degraded

Possible causes:

- stale score
- recent scheduler failure
- Prometheus query error
- dependency-check failure
- database issue

Problem: application cannot query Kubernetes

Possible causes:

- service account not mounted or not used
- RBAC missing or too restrictive
- `KUBERNETES_IN_CLUSTER` misconfigured

### 20. Why this deployment model is strong

This Kubernetes deployment model is strong because it makes the project:

- self-contained
- reproducible
- platform-native
- operationally inspectable
- CI/CD-consumable
- dashboard-compatible

It also reflects production-style concerns such as:

- secrets and config separation
- non-root execution
- health probes
- persistent database storage
- RBAC
in-cluster service discovery

This is one of the reasons the project feels like a real platform service rather than a standalone script.

### 21. Kubernetes deployment summary

Running deploy-confidence-service in Kubernetes allows the project to behave as intended:

- collect in-cluster platform signals
- persist deployment-confidence history
- expose APIs with proper readiness and health semantics
- support dashboard visualization
- support CI/CD deployment gating

> The Kubernetes deployment is therefore not just a packaging step. 
> It is the runtime model that makes the architecture complete.




## Grafana Setup




## End-to-End Workflow

This section explains the full operational workflow of `deploy-confidence-service` from signal collection to deployment control.

The goal is to show how the system behaves as a complete platform component, not just as an isolated API or dashboard.

At a high level, the workflow is:

1. raw signals are collected
2. deployment confidence is computed
3. results are stored
4. APIs expose the latest decision
5. Grafana visualizes the decision history
6. CI/CD pipelines consume the decision before deployment

This is the end-to-end path that turns observability into release-control intelligence.

---

## Why the end-to-end workflow matters

The value of this project is not in any one individual part by itself.

- Prometheus alone is not enough
- Kubernetes events alone are not enough
- PostgreSQL alone is not enough
- Grafana alone is not enough
- an API alone is not enough

The real value appears when these parts work together as one decision system.

The workflow is important because it shows:

- where the data comes from
- how the service processes it
- how the result becomes durable
- how humans inspect it
- how pipelines enforce it

That is what makes the project operationally meaningful.

---

## Step 1 — Raw platform signals are gathered

The workflow begins with **signal collection**.

The service gathers three main categories of deployment-relevant input:

### 1. Prometheus metrics
The Prometheus collector retrieves platform metrics such as:
- worker node headroom
- restart-related workload pressure

These metrics help determine whether the cluster has enough stability and capacity for rollout.

### 2. Kubernetes state and events
The Kubernetes collector inspects:
- pod state
- Kubernetes events
- rollout-related warning signals

This is how the service detects signals such as:
- image pull failures
- startup latency behavior

### 3. Dependency checks
The service also performs active checks for:
- DNS resolution
- registry reachability

These checks are important because deployment trust depends not only on internal cluster health, but also on the delivery path required to perform deployment successfully.

### What this step means
This step answers:

**What is the current rollout-relevant state of the platform?**

It does not yet answer whether deployment should proceed.  
It only gathers the raw evidence required to make that decision.

---

## Step 2 — Raw inputs are normalized and scored

Once the collectors finish, the raw inputs are passed into the **scoring engine**.

The scoring engine performs several actions:

- normalizes each raw input into a bounded component score
- applies a weight to each component
- computes the final weighted score
- assigns a deployment status
- generates a short summary

### Current scoring components
The service currently evaluates:

- node headroom
- restart pressure
- image pull health
- startup latency
- dependency health

### Outputs generated by the scoring engine
At the end of this step, the system produces:

- a final score from `0` to `100`
- a status:
  - `DEPLOY`
  - `CAUTION`
  - `HOLD`
- a `deploy_allowed` flag
- a summary explanation
- per-component breakdown data

### What this step means
This step answers:

**Given the observed platform state, how trustworthy is this environment for deployment right now?**

This is the point where raw observability becomes a deployment decision.

---

## Step 3 — The result is persisted to PostgreSQL

After the scoring engine finishes, the result is written to PostgreSQL.

This persistence step stores both:
- the top-level score run
- the detailed component breakdown

### Stored records
The service writes:

#### One row to `score_runs`
This includes:
- calculation time
- final score
- status
- deploy allowed
- threshold
- summary

#### Multiple rows to `score_components`
This includes:
- component name
- component score
- weight
- reason
- raw payload

### Why this step matters
This is what turns the service into a historical decision engine.

Without persistence, the service would only provide:
- the current score in memory

With persistence, it provides:
- history
- trends
- explanation over time
- dashboard queries
- auditability
- repeatable CI/CD evidence

### What this step means
This step answers:

**Can this deployment decision be stored, explained, and reviewed later?**

---

## Step 4 — Scheduler keeps the decision stream fresh

The service is not designed as a one-time evaluator.

It includes a scheduler that runs continuously.

### Scheduler behavior
At startup, the service:

1. initializes database tables
2. performs an immediate score update
3. starts the recurring scheduler

Then, on every configured interval, it:

- collects signals again
- recomputes the score
- persists a new score run
- updates freshness state
- records failure context if something goes wrong

### Why this matters
This makes the system a **continuous deployment-confidence stream** instead of an on-demand script.

That is important because:
- Grafana needs historical and fresh data
- readiness depends on recent score generation
- CI/CD pipelines need a trustworthy current result
- operators need to know whether the score is still valid

### What this step means
This step answers:

**Is the deployment-confidence decision still current enough to trust?**

---

## Step 5 — FastAPI exposes operational and decision endpoints

Once score runs are being generated and stored, the service exposes that information through the FastAPI API.

### Operational endpoints
These endpoints describe the state of the service itself:

- `/live`
- `/ready`
- `/health`

### Decision endpoints
These endpoints describe the state of deployment confidence:

- `/score`
- `/details`

### Why this matters
The API is the machine-readable interface of the system.

It allows:
- Kubernetes to probe the service
- operators to inspect it
- dashboards to compare expected state
- CI/CD pipelines to enforce deployment policy

### What this step means
This step answers:

**How do machines and operators consume the service?**

---

## Step 6 — Grafana visualizes the stored decision history

Grafana provides the human-facing operational view of the system.

It reads the stored score history from PostgreSQL and visualizes:

- current confidence score
- deployment status
- deploy allowed
- freshness
- component breakdown
- score trends
- recent decision history

### Why Grafana reads PostgreSQL
For this project, Grafana should not reconstruct the decision from raw Prometheus metrics.

Instead, it visualizes the actual stored outputs of the service.

This is important because it ensures the dashboard matches:
- the API
- the scheduler output
- the persisted decision model

### What this step means
This step answers:

**How do humans understand and inspect the deployment-confidence result?**

---

## Step 7 — CI/CD consumes the decision before deployment

The final operational consumer is the deployment pipeline.

A CI/CD pipeline can query the service before rollout and use it as a deployment gate.

### Typical CI/CD flow
A consumer pipeline can:

1. call `/ready`
2. call `/health`
3. verify service trust and score freshness
4. call `/score`
5. compare score against environment threshold
6. call `/details` for explanation if needed
7. allow or block deployment

### Environment policy example
The same service can enforce different thresholds depending on environment, such as:

- `dev` → `60`
- `staging` → `75`
- `prod` → `85`

A stricter production policy may also block:
- `CAUTION`
- `HOLD`

### Why this matters
This is the point where the project becomes more than observability.

It becomes a **deployment decision control**.

Instead of only showing risk, the system can actively prevent risky rollouts before they happen.

### What this step means
This step answers:

**How does the service influence real release behavior?**

---

## Full workflow summary

The end-to-end workflow can be summarized below:

![img](img/orch-10.png)


### Practical runtime lifecycle

A practical runtime sequence looks like this:

On service startup
- app starts
- tables are initialized
- first score run is attempted
- scheduler starts
- readiness becomes meaningful once a fresh score exists

During normal operation
- scheduler runs continuously
- new score runs are written
- dashboard updates over time
- APIs expose the latest decision
- CI/CD pipelines can query the service at any time

During degradation
- collector failures may prevent updates
- freshness may eventually fail
- /ready may return false
- /health may become degraded
- CI/CD should stop trusting the service until freshness returns

This is one of the strongest design aspects of the project because it treats deployment trust as something that must remain operationally fresh.

### Why this workflow is useful

This workflow is useful because it connects multiple concerns that are often handled separately:

- observability
- deployment trust
- persistence
- dashboarding
- release control

Normally, teams inspect these manually across several systems.

Here, the workflow makes them part of a single, repeatable operational loop.

That creates a much stronger platform story.

### What this workflow proves

The end-to-end flow proves that the project is not just:

- a scoring script
- a dashboard
- an API
- a database-backed service

It is a complete decision system that:

- collects platform signals
- evaluates deployment trust
- stores that evaluation over time
- explains it visually
- exposes it programmatically
- uses it to influence real deployments

That is what makes the overall architecture strong from a platform engineering and SRE perspective.

### End-to-end workflow summary in one sentence

> deploy-confidence-service continuously converts rollout-relevant platform signals into a stored, explainable deployment decision that humans inspect in Grafana and CI/CD pipelines enforce before deployment.







## Why This Matters

`deploy-confidence-service` matters because it addresses a gap that many platform and SRE teams still handle manually:

**turning infrastructure signals into a trustworthy deployment decision**

Most environments already have observability.

They have:
- Prometheus
- Grafana
- Kubernetes events
- dashboards
- alerts
- logs

But many teams still do not have a consistent answer to one very practical release question:

**Should we deploy right now?**

That judgment is often made informally by looking at several dashboards and deciding whether the platform “feels healthy enough.”

This project exists to make that decision:
- measurable
- repeatable
- explainable
- automatable

---

## Why this matters for platform engineering

Platform engineering is not only about building tools. It is about creating reliable internal capabilities that make delivery safer and more consistent.

`deploy-confidence-service` fits that model because it acts as a reusable platform capability.

It gives teams:

- one consistent deployment-confidence model
- one API for deployment trust
- one dashboard for human visibility
- one historical decision record
- one CI/CD-consumable release gate

This is useful because it reduces the need for every deployment team to interpret raw platform conditions differently.

Instead of many people making different judgment calls, the platform can provide one shared deployment-confidence service.

That is a strong platform engineering pattern.

---

## Why this matters for SRE

From an SRE perspective, the project is valuable because it shifts attention from pure system availability to **release safety under current platform conditions**.

A system can be:
- up
- green in dashboards
- passing general probes

and still be a poor deployment target.

Examples include:
- image pulls failing intermittently
- startup latency increasing
- worker headroom shrinking
- dependencies becoming unstable
- score freshness degrading

This project makes those rollout-relevant conditions visible and actionable.

It allows SRE-style reasoning such as:

- Is the system merely alive, or trustworthy for deployment?
- Is the score fresh enough to trust?
- Are current rollout conditions degrading?
- Should new change be blocked until platform trust recovers?

That makes the project more aligned with real reliability engineering than a simple status dashboard.

---

## Why this matters for release safety

One of the strongest reasons this project matters is that it connects observability directly to release control.

Without this kind of service, many teams still make deployment decisions based on:
- intuition
- inconsistent manual review
- incomplete visibility
- optimistic assumptions about cluster health

With `deploy-confidence-service`, deployment trust becomes part of the release workflow itself.

The service can:
- evaluate current platform conditions
- expose a machine-readable decision
- explain why confidence is low
- block deployment when risk is too high

This is important because risky deployments often happen not because teams lack telemetry, but because they lack a consistent decision layer on top of that telemetry.

This project provides that decision layer.

---

## Why this matters beyond dashboards

Many engineers naturally ask:

**Why not just use Prometheus and Grafana?**

That is a reasonable question.

The answer is that Prometheus and Grafana solve different problems.

### Prometheus
Prometheus tells you:
- what is happening
- how metrics are changing
- what can be alerted on

### Grafana
Grafana shows you:
- how the signals look
- how to correlate them visually
- where to investigate

### Deploy-Confidence-Service
This service tells you:
- how those signals combine into deployment trust
- whether the current platform is safe enough to deploy into
- what is reducing deployment confidence
- whether CI/CD should continue or block rollout

That is why the project matters.

It is not trying to replace observability.  
It is trying to add a **decision layer** on top of observability.

---

## Why this matters for engineers and operators

For engineers and operators, the project provides a more structured way to reason about rollout risk.

Instead of manually piecing together:
- node pressure
- restarts
- pull failures
- dependency status
- dashboards
- recent failures

the service gives them:

- one score
- one status
- one explanation
- one dashboard
- one history trail

This makes decision-making faster and more transparent.

It also reduces ambiguity when teams ask:
- why was deployment blocked?
- why was deployment allowed?
- what is the main current risk?
- has this been getting worse over time?

Those are practical operational benefits.

---

## Why this matters for leadership and business context

For engineering managers, CTOs, and platform leaders, the value is not only technical.

It is also organizational.

A service like this can help reduce:
- inconsistent deployment decisions
- rollout risk driven by poor timing
- avoidable release failures
- wasted engineering time during incident triage
- confusion about whether platform conditions were trustworthy

It creates a stronger link between:
- platform state
- release safety
- operational trust

That matters because unreliable deployment conditions often translate into:
- slower delivery
- more rollback risk
- more firefighting
- less confidence in the platform

A service that standardizes deployment trust can improve both engineering consistency and operational clarity.

---

## Why this matters as a portfolio project

This project is valuable as a portfolio artifact because it demonstrates more than one technical skill.

It shows:

- Kubernetes understanding
- observability integration
- FastAPI service design
- PostgreSQL persistence
- scoring and decision modeling
- health/readiness/liveness semantics
- Grafana dashboard design
- CI/CD integration
- deployment safety thinking
- platform engineering mindset

That combination is important.

Many projects show monitoring.
Many projects show APIs.
Many projects show dashboards.

Fewer projects show how to:
- turn platform signals into a decision model
- persist and explain that model
- visualize it for humans
- expose it to CI/CD
- use it to block risky deployments

That makes the project distinctive.

---

## Why this matters for platform maturity

A mature platform is not only one that runs workloads.

It is one that helps teams make better deployment decisions.

`deploy-confidence-service` contributes to that maturity by introducing:

- structured rollout trust evaluation
- explicit score freshness logic
- operational health semantics
- historical decision visibility
- machine-readable deployment policy inputs

These are the kinds of ideas that move a platform from:
- reactive observability
to
- proactive release safety

That is a meaningful architectural shift.

---

## Why this matters in day-to-day operations

In day-to-day operations, the service can change how teams think about deployment timing.

Instead of asking only:
- Is the cluster up?

teams can also ask:
- Is the cluster currently trustworthy for rollout?

That difference matters.

A cluster being up does not guarantee:
- registry access is stable
- startup behavior is healthy
- capacity is sufficient
- rollouts will behave well

The service captures that nuance and turns it into something usable.

This makes day-to-day operations more disciplined and less guess-based.

---

## Why the project is stronger because of persistence and history

Another reason this project matters is that it does not only give a live answer.

It keeps historical evidence.

That means the service can help answer:
- Has deployment confidence been drifting downward?
- Was the platform already weak before a failed rollout?
- Which component keeps recurring as a risk?
- Was a blocked pipeline decision justified at the time?

That historical dimension makes the service useful not just for live gating, but also for:
- release review
- troubleshooting
- post-incident analysis
- score-model tuning

That makes the project operationally richer than a one-time gate check.

---

## Why the CI/CD integration matters most

The CI/CD integration is one of the strongest parts of the project because it proves the service has real impact.

It is one thing to say:
- here is a confidence score

It is another to say:
- the deployment pipeline used that score and blocked release

That is where the project becomes strategically important.

It shows that the service is not only descriptive.
It is also **enforceable**.

That is what makes it a true platform control point rather than just an observability convenience.

---

## The core strategic value

The core strategic value of the project is this:

**It standardizes how deployment trust is evaluated.**

Instead of:
- subjective interpretation
- inconsistent rollout decisions
- over-reliance on broad cluster health

it provides:
- structured signal collection
- consistent score calculation
- explainable risk breakdown
- historical decision context
- CI/CD consumption path

That is why it matters.

It gives the platform a reusable answer to a question that is usually handled informally.

---

## In one sentence

`deploy-confidence-service` matters because it turns raw platform observability into an explainable, persistent, and CI/CD-consumable deployment decision system.

---

## Summary

This project matters because it sits at the intersection of:

- **observability**
- **platform engineering**
- **SRE**
- **release safety**
- **automation**

It helps answer a question that many teams still handle manually:

**Can we trust this platform enough to deploy right now?**

And instead of leaving that answer to intuition, it provides:
- a score
- a status
- a dashboard
- an API
- a deployment gate
- a history trail

That is what makes the project valuable technically, operationally, and strategically.




## Future Improvements

`deploy-confidence-service` is already functional as a Kubernetes-native deployment decision service, but there are several areas where it can be extended and hardened further.

These improvements fall into a few categories:

- scoring model maturity
- runtime hardening
- CI/CD policy sophistication
- observability of the service itself
- packaging and deployment ergonomics
- broader platform integration

This section outlines realistic next steps that would strengthen the system further.

---

## 1. Refine the scoring model

The current scoring model is intentionally transparent and easy to reason about, which is a strength. But it can still be improved over time.

### Possible improvements

- refine normalization thresholds based on real cluster history
- tune weights per environment or cluster type
- add more rollout-specific signals
- distinguish between soft degradation and hard failure more precisely
- calibrate the model using real incidents and blocked deployments

### Examples

Potential future signals could include:
- unschedulable pod pressure
- control-plane API error rates
- storage latency or PVC attach delays
- node NotReady frequency
- container OOM trends
- admission webhook error rates
- network policy deny spikes

The goal would be to improve decision quality without making the model opaque.

---

## 2. Improve startup-latency measurement

The current startup-latency component is a useful MVP signal, but it can be refined.

### Current limitation
The MVP implementation estimates startup behavior from pod creation and startup timestamps.

### Future improvement ideas
- use readiness transition timing instead of start time alone
- track deployment rollout completion latency
- distinguish image-pull delay from application startup delay
- compare startup latency across namespaces or deployment classes
- calculate stronger percentiles and windowing logic

This would make the rollout-timing signal more precise and operationally meaningful.

---

## 3. Expand dependency checks

The current dependency checks focus on:
- DNS resolution
- registry reachability

These are strong first checks, but real deployment paths often include additional dependencies.

### Future improvement ideas
- validate internal artifact repository access
- validate Helm chart repository reachability
- validate Git/SCM access for GitOps-style deployments
- validate ingress/controller reachability
- validate Kubernetes API latency thresholds
- validate object storage if deployment relies on it

This would make the confidence model more representative of full delivery-path health.

---

## 4. Export service metrics

Right now, the service exposes APIs and stores history in PostgreSQL, but it does not yet expose its own metrics as a Prometheus scrape target.

### Why this would matter
Adding service-native metrics would make the service itself more observable.

Examples:
- scheduler run count
- scheduler success/failure count
- score update duration
- last score age
- current status distribution
- collector failure counts
- component score distribution

This would allow the platform to monitor the confidence service itself using Prometheus in addition to the current health endpoints.

---

## 5. Add service-native alerts

Once service metrics exist, the next natural step is alerting.

### Possible alert conditions
- score freshness stale
- repeated scheduler failures
- confidence status remains `HOLD` for too long
- repeated dependency-check failures
- repeated image-pull degradation
- no score runs generated for an abnormal time window

This would turn the service into not just a passive decision engine, but an actively monitored platform component.

---

## 6. Improve CI/CD policy logic

The current CI/CD gate is already strong, but it can be made more sophisticated.

### Future improvements
- require manual approval for `CAUTION` in production
- allow override with audit trail
- add different policies for different application criticality tiers
- add namespace- or workload-specific policy rules
- block deployments if service health is degraded for certain reasons only
- enrich pipeline summaries with direct component breakdown rendering
- support rollback triggers based on post-deploy confidence degradation

This would make the gate model more flexible and realistic for larger organizations.

---

## 7. Add post-deploy verification mode

The service currently focuses on **pre-deploy** trust, but it could also support **post-deploy** verification.

### Example use case
After a deployment completes:
- query the service again
- compare pre-deploy and post-deploy confidence
- detect if the rollout materially degraded platform trust
- trigger rollback or alert if confidence collapses

This would extend the service from a pre-deploy gate into a broader rollout-safety system.

---

## 8. Tighten RBAC further

The current RBAC model is read-only, which is good, but it can still be tightened depending on operational scope.

### Future improvements
- restrict collectors to selected namespaces
- avoid cluster-wide visibility where not required
- separate roles for different deployment modes
- allow namespace-scoped operation for smaller clusters or tenant isolation

This would improve security posture further while preserving the same architectural model.

---

## 9. Improve PostgreSQL deployment model further

The in-cluster PostgreSQL model is useful and self-contained, but there are stronger production options depending on scale and reliability needs.

### Future improvements
- move fully to StatefulSet if not already done
- use backup strategy for score history
- define retention policy for old score runs
- add automatic pruning or archival logic
- move to managed PostgreSQL in more production-oriented environments

This would make persistence more resilient and scalable over time.

---

## 10. Add retention and cleanup policy

As score runs continue to accumulate, retention becomes important.

### Future improvements
- keep detailed score runs for a short recent period
- aggregate or archive older results
- delete very old component rows after retention threshold
- add configurable history windows

This matters because long-running environments can accumulate significant historical data over time.

---

## 11. Package with Helm or Kustomize

The current Kubernetes manifests are strong, but packaging can be improved further.

### Future improvements
- create a Helm chart for the service
- create environment overlays with Kustomize
- support configuration variation by environment
- simplify deploy-confidence installation into new clusters

This would make the service easier to reuse and deploy in other environments.

---

## 12. Support multiple cluster profiles

The current design assumes one deployment-confidence model per deployed service instance.

A future extension could support:
- different cluster profiles
- environment-specific scoring rules
- multiple namespaces or trust domains
- separate decision models for different workload classes

This would make the service more adaptable across diverse platform contexts.

---

## 13. Add multi-environment awareness

The service can already support environment thresholds in CI/CD, but a future improvement would be to make environment context more explicit in the service itself.

### Possible improvements
- persist environment-specific score runs
- support separate score histories per environment
- support environment-aware dashboard filtering
- expose environment-aware policies from the service directly

This would help if the same service instance is used across multiple deployment stages.

---

## 14. Add authentication and authorization

The current API model is suitable for internal trusted environments, but stronger access control may be desirable later.

### Future improvements
- add API authentication
- restrict sensitive endpoints
- enforce service-to-service trust
- protect score and details endpoints from unintended consumers

This would matter more in shared or externally reachable environments.

---

## 15. Add a service UI or richer frontend

Grafana is the right dashboard for the current architecture, but a future enhancement could be a lightweight service-native frontend.

### Possible future capabilities
- current score page
- component drilldown
- failure explanation view
- score history explorer
- deployment gate audit history

This is not necessary now, but it could become useful if the project evolves into a larger internal platform service.

---

## 16. Support anomaly-aware scoring

The current model uses explicit thresholds and rule-based scoring. A future direction could include anomaly-aware evaluation while keeping the final decision explainable.

### Examples
- compare restart pressure against recent historical baseline
- detect unusual startup-latency behavior relative to last 24 hours
- detect sudden image-pull degradation rather than only absolute counts

This could improve signal quality while still preserving transparency.

---

## 17. Add deployment-context awareness

Another future improvement would be to incorporate deployment context itself.

### Examples
- number of workloads about to roll out
- rollout size
- application criticality
- namespace sensitivity
- whether current rollout includes stateful workloads

This would allow the service to reason not only about platform state, but about deployment impact relative to that state.

---

## 18. Add richer audit and decision evidence

The service already stores strong decision history, but it could be extended with richer evidence.

### Future improvements
- persist health-state snapshot alongside score runs
- persist CI/CD gate results
- persist which pipeline or environment consumed the decision
- persist override or manual approval metadata

This would strengthen auditability and release review workflows.

---

## 19. Add automated test expansion

The project already includes useful tests, but future test coverage can grow further.

### Future improvements
- integration tests against a real PostgreSQL instance
- Kubernetes client integration tests
- scheduler timing tests
- API contract tests
- container-level smoke tests
- Kubernetes deployment tests in a test cluster

This would increase confidence in the service as it evolves.

---

## 20. Improve documentation structure

The README is the main entry point, but future documentation can be expanded into a `docs/` structure.

### Possible additions
- `docs/architecture.md`
- `docs/scoring-model.md`
- `docs/dashboard.md`
- `docs/deployment.md`
- `docs/cicd.md`

This would make the project easier to navigate as it grows.

---

## 21. Add example consumer applications

The CI/CD gate is already demonstrated conceptually, but future portfolio polish could include:
- one sample consumer app
- one sample deployment blocked by confidence policy
- one sample deployment allowed by policy
- screenshots or evidence of both cases

This would make the project even easier to demonstrate end-to-end.

---

## 22. Add failure simulation scenarios

A powerful future enhancement would be to document or automate controlled failure scenarios that degrade the score in known ways.

### Example scenarios
- inject image-pull failures
- simulate registry unreachability
- simulate dependency-check failures
- generate restart pressure
- reduce worker headroom

This would make the dashboard and pipeline behavior easier to demonstrate and validate.

---

## 23. Evolve from score service to release-trust platform component

The long-term future of this project could be broader than a single service.

It could evolve into:
- a reusable rollout-trust service
- a deployment policy platform component
- a standard pre-deploy control point
- a release-safety intelligence layer

That would make it valuable not only as a project, but as a pattern for platform teams.

---

## Summary

The current project already demonstrates a strong end-to-end system:

- collectors
- scoring model
- persistence
- API
- dashboard
- health semantics
- Kubernetes deployment
- CI/CD integration

The future improvements above are not required for the project to be useful.

They represent the next layer of maturity:
- more precision
- more hardening
- more automation
- more observability
- more policy sophistication

That means the project already stands on its own, while still having a clear path for future growth.

The core idea remains the same:

**turn rollout-relevant platform signals into an explainable, persistent, and enforceable deployment-confidence decision.**
















## Deploy-Confidence-Service

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
- Architecture outcome

The result of this architecture is a platform service that sits between observability and delivery.

It does not simply show what is happening.

It answers a more operationally important question:

Given the current platform state, how safe is it to deploy right now?

That makes the architecture useful not only for visibility, but for real release-control decisions.


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

That makes the architecture realistic for platform engineering and SRE use cases.

The service is not just telling you what is happening.

It is telling you whether the platform is currently trustworthy enough to deploy.



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

deploy-confidence-service continuously converts rollout-relevant platform signals into a stored, explainable deployment decision that humans inspect in Grafana and CI/CD pipelines enforce before deployment.




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

the model gives platform teams a more operationally mature way to reason about rollout safety.
























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

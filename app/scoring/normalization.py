from app.constants import (
    COMPONENT_DEPENDENCY_HEALTH,
    COMPONENT_IMAGE_PULL_HEALTH,
    COMPONENT_NODE_HEADROOM,
    COMPONENT_RESTART_PRESSURE,
    COMPONENT_STARTUP_LATENCY,
)


def score_node_headroom(*, max_worker_cpu_pct: float, max_worker_mem_pct: float) -> tuple[float, str, dict]:
    worst_pct = max(max_worker_cpu_pct, max_worker_mem_pct)

    if worst_pct < 60:
        score = 100.0
        reason = "Workers have strong CPU and memory headroom."
    elif worst_pct < 75:
        score = 80.0
        reason = "Workers have acceptable CPU and memory headroom."
    elif worst_pct < 85:
        score = 50.0
        reason = "Worker headroom is tightening and may affect rollout safety."
    else:
        score = 20.0
        reason = "Worker headroom is critically low for safe rollout."

    raw = {
        "max_worker_cpu_pct": max_worker_cpu_pct,
        "max_worker_mem_pct": max_worker_mem_pct,
    }
    return score, reason, raw


def score_restart_pressure(*, recent_restarts_15m: int) -> tuple[float, str, dict]:
    if recent_restarts_15m <= 2:
        score = 100.0
        reason = "Restart pressure is low across monitored workloads."
    elif recent_restarts_15m <= 5:
        score = 75.0
        reason = "Restart pressure is elevated but still manageable."
    elif recent_restarts_15m <= 10:
        score = 40.0
        reason = "Restart pressure is high and indicates workload instability."
    else:
        score = 10.0
        reason = "Restart pressure is critically high."

    raw = {
        "recent_restarts_15m": recent_restarts_15m,
    }
    return score, reason, raw

def score_image_pull_health(
    *,
    pull_failures_15m: int,
    active_pull_failures: int = 0,
    recent_pull_failure_events: int | None = None,
    affected_pods: list[str] | None = None,
    affected_registries: list[str] | None = None,
    window_minutes: int = 15,
) -> tuple[float, str, dict]:
    affected_pods = affected_pods or []
    affected_registries = affected_registries or []
    recent_pull_failure_events = (
        pull_failures_15m if recent_pull_failure_events is None else recent_pull_failure_events
    )

    # Active blocker takes priority
    if active_pull_failures > 0:
        if active_pull_failures == 1:
            score = 0.0
            reason = "Active image pull failure is currently blocking rollout confidence."
        else:
            score = 0.0
            reason = "Multiple active image pull failures are currently blocking rollout confidence."

    # Recent instability is softer than active failure
    elif recent_pull_failure_events == 0:
        score = 100.0
        reason = "No active or recent image pull failures detected."
    elif recent_pull_failure_events == 1:
        score = 75.0
        reason = "A recent image pull failure slightly reduced rollout confidence."
    elif recent_pull_failure_events <= 3:
        score = 45.0
        reason = "Recent image pull failures reduced rollout confidence."
    else:
        score = 15.0
        reason = "Repeated recent image pull failures indicate major rollout risk."

    raw = {
        "pull_failures_15m": pull_failures_15m,
        "active_pull_failures": active_pull_failures,
        "recent_pull_failure_events": recent_pull_failure_events,
        "affected_pods": affected_pods,
        "affected_registries": affected_registries,
        "window_minutes": window_minutes,
    }
    return score, reason, raw

# def score_image_pull_health(
#     *,
#     pull_failures_15m: int,
#     affected_registries: list[str] | None = None,
# ) -> tuple[float, str, dict]:
#     affected_registries = affected_registries or []
#
#     if pull_failures_15m == 0:
#         score = 100.0
#         reason = "No recent image pull failures detected."
#     elif pull_failures_15m == 1:
#         score = 75.0
#         reason = "A recent image pull failure slightly reduced rollout confidence."
#     elif pull_failures_15m <= 3:
#         score = 45.0
#         reason = "Recent image pull failures reduced rollout confidence."
#     else:
#         score = 15.0
#         reason = "Repeated image pull failures present a major rollout risk."
#
#     raw = {
#         "pull_failures_15m": pull_failures_15m,
#         "affected_registries": affected_registries,
#     }
#     return score, reason, raw

def score_startup_latency(
    *, p95_startup_seconds: float, sample_count: int = 0
) -> tuple[float, str, dict]:
    if sample_count == 0:
        score = 50.0
        reason = "Pod startup latency is unavailable because no valid startup samples were found."
    elif p95_startup_seconds < 30:
        score = 100.0
        reason = "Pod startup latency is healthy."
    elif p95_startup_seconds < 60:
        score = 70.0
        reason = "Pod startup latency is elevated but still within tolerable range."
    elif p95_startup_seconds < 120:
        score = 40.0
        reason = "Pod startup latency is high and may delay safe rollout."
    else:
        score = 10.0
        reason = "Pod startup latency is critically high."

    raw = {
        "p95_startup_seconds": p95_startup_seconds,
        "sample_count": sample_count,
    }
    return score, reason, raw

# def score_startup_latency(*, p95_startup_seconds: float) -> tuple[float, str, dict]:
#     if p95_startup_seconds < 30:
#         score = 100.0
#         reason = "Pod startup latency is healthy."
#     elif p95_startup_seconds < 60:
#         score = 70.0
#         reason = "Pod startup latency is elevated but still within tolerable range."
#     elif p95_startup_seconds < 120:
#         score = 40.0
#         reason = "Pod startup latency is high and may delay safe rollout."
#     else:
#         score = 10.0
#         reason = "Pod startup latency is critically high."
#
#     raw = {
#         "p95_startup_seconds": p95_startup_seconds,
#     }
#     return score, reason, raw


def score_dependency_health(*, dns_ok: bool, registry_ok: bool) -> tuple[float, str, dict]:
    if dns_ok and registry_ok:
        score = 100.0
        reason = "Critical deployment dependencies are currently reachable."
    elif dns_ok or registry_ok:
        score = 60.0
        reason = "One critical deployment dependency is degraded."
    else:
        score = 10.0
        reason = "Critical deployment dependencies are failing."

    raw = {
        "dns_ok": dns_ok,
        "registry_ok": registry_ok,
    }
    return score, reason, raw


COMPONENT_NORMALIZERS = {
    COMPONENT_NODE_HEADROOM: score_node_headroom,
    COMPONENT_RESTART_PRESSURE: score_restart_pressure,
    COMPONENT_IMAGE_PULL_HEALTH: score_image_pull_health,
    COMPONENT_STARTUP_LATENCY: score_startup_latency,
    COMPONENT_DEPENDENCY_HEALTH: score_dependency_health,
}
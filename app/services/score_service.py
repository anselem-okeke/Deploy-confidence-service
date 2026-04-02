from app.collectors.dependency_checks import DependencyChecker
from app.collectors.kubernetes_collector import KubernetesCollector
from app.collectors.prometheus_collector import PrometheusCollector
from app.config import settings
from app.scoring.engine import ScoreCalculationResult, calculate_deployment_confidence
from app.services.persistence_service import get_latest_score_run
from app.schemas.score import (
    ScoreComponentResponse,
    ScoreDetailsResponse,
    ScoreResponse,
)


def _to_iso_z(dt) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def get_latest_score_response(db) -> ScoreResponse | None:
    score_run = get_latest_score_run(db)
    if score_run is None:
        return None

    return ScoreResponse(
        score=float(score_run.total_score),
        status=score_run.status,
        deploy_allowed=score_run.deploy_allowed,
        threshold=score_run.threshold,
        summary=score_run.summary,
        updated_at=_to_iso_z(score_run.calculated_at),
    )


def get_latest_score_details_response(db) -> ScoreDetailsResponse | None:
    score_run = get_latest_score_run(db)
    if score_run is None:
        return None

    components = [
        ScoreComponentResponse(
            name=component.component_name,
            score=float(component.component_score),
            weight=float(component.weight),
            reason=component.reason,
            raw=component.raw_payload,
        )
        for component in score_run.components
    ]

    return ScoreDetailsResponse(
        score=float(score_run.total_score),
        status=score_run.status,
        deploy_allowed=score_run.deploy_allowed,
        threshold=score_run.threshold,
        summary=score_run.summary,
        updated_at=_to_iso_z(score_run.calculated_at),
        components=components,
    )


def collect_raw_inputs(
    prometheus_collector: PrometheusCollector | None = None,
    kubernetes_collector: KubernetesCollector | None = None,
    dependency_checker: DependencyChecker | None = None,
) -> dict:
    prometheus_collector = prometheus_collector or PrometheusCollector()
    kubernetes_collector = kubernetes_collector or KubernetesCollector()
    dependency_checker = dependency_checker or DependencyChecker()

    raw_inputs: dict = {}
    raw_inputs.update(prometheus_collector.collect_prometheus_inputs())
    raw_inputs.update(kubernetes_collector.collect_kubernetes_inputs())
    raw_inputs["dependency_health"] = dependency_checker.collect_dependency_health()

    return raw_inputs


def calculate_current_deployment_confidence(
    prometheus_collector: PrometheusCollector | None = None,
    kubernetes_collector: KubernetesCollector | None = None,
    dependency_checker: DependencyChecker | None = None,
) -> ScoreCalculationResult:
    raw_inputs = collect_raw_inputs(
        prometheus_collector=prometheus_collector,
        kubernetes_collector=kubernetes_collector,
        dependency_checker=dependency_checker,
    )

    result = calculate_deployment_confidence(
        raw_inputs=raw_inputs,
        threshold=settings.deploy_threshold,
    )

    return result
from dataclasses import dataclass

from app.constants import DEFAULT_COMPONENT_WEIGHTS
from app.scoring.normalization import COMPONENT_NORMALIZERS
from app.scoring.thresholds import classify_score, deploy_allowed


@dataclass
class ComponentScoreResult:
    name: str
    score: float
    weight: float
    reason: str
    raw: dict


@dataclass
class ScoreCalculationResult:
    total_score: float
    status: str
    deploy_allowed: bool
    threshold: int
    summary: str
    components: list[ComponentScoreResult]


def build_component_scores(raw_inputs: dict, weights: dict | None = None) -> list[ComponentScoreResult]:
    weights = weights or DEFAULT_COMPONENT_WEIGHTS
    results: list[ComponentScoreResult] = []

    for component_name, normalizer in COMPONENT_NORMALIZERS.items():
        if component_name not in raw_inputs:
            raise ValueError(f"Missing raw input for component '{component_name}'")

        component_input = raw_inputs[component_name]
        score, reason, raw = normalizer(**component_input)

        results.append(
            ComponentScoreResult(
                name=component_name,
                score=round(float(score), 2),
                weight=float(weights[component_name]),
                reason=reason,
                raw=raw,
            )
        )

    return results


def calculate_total_score(components: list[ComponentScoreResult]) -> float:
    total = sum(component.score * component.weight for component in components)
    return round(total, 2)


def build_summary(components: list[ComponentScoreResult]) -> str:
    sorted_components = sorted(components, key=lambda c: c.score)
    lowest = sorted_components[:2]

    if len(lowest) == 0:
        return "No component results available."

    if len(lowest) == 1:
        return f"{lowest[0].name.replace('_', ' ')} is the main factor affecting deployment confidence."

    return (
        f"{lowest[0].name.replace('_', ' ')} and "
        f"{lowest[1].name.replace('_', ' ')} are the main factors affecting deployment confidence."
    )


def calculate_deployment_confidence(
    *,
    raw_inputs: dict,
    threshold: int,
    weights: dict | None = None,
) -> ScoreCalculationResult:
    components = build_component_scores(raw_inputs=raw_inputs, weights=weights)
    total_score = calculate_total_score(components)
    status = classify_score(total_score)
    allowed = deploy_allowed(total_score, threshold)
    summary = build_summary(components)

    return ScoreCalculationResult(
        total_score=total_score,
        status=status,
        deploy_allowed=allowed,
        threshold=threshold,
        summary=summary,
        components=components,
    )
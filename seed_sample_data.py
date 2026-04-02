from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.services.persistence_service import create_score_component, create_score_run


def main() -> None:
    db = SessionLocal()
    try:
        score_run = create_score_run(
            db,
            total_score=78.5,
            status="CAUTION",
            deploy_allowed=True,
            threshold=70,
            summary="Image pull health and startup latency reduced rollout confidence.",
            calculated_at=datetime.now(timezone.utc),
        )

        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name="node_headroom",
            component_score=82.0,
            weight=0.25,
            reason="Workers have moderate CPU and memory headroom.",
            raw_payload={
                "max_worker_cpu_pct": 61,
                "max_worker_mem_pct": 67,
            },
        )

        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name="restart_pressure",
            component_score=90.0,
            weight=0.20,
            reason="Restart pressure is low across monitored workloads.",
            raw_payload={
                "recent_restarts_15m": 1,
            },
        )

        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name="image_pull_health",
            component_score=45.0,
            weight=0.25,
            reason="Recent image pull failures reduced rollout confidence.",
            raw_payload={
                "pull_failures_15m": 3,
                "affected_registries": ["quay.io"],
            },
        )

        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name="startup_latency",
            component_score=70.0,
            weight=0.15,
            reason="Pod startup latency is elevated but still within tolerable range.",
            raw_payload={
                "p95_startup_seconds": 48,
            },
        )

        create_score_component(
            db,
            score_run_id=score_run.id,
            component_name="dependency_health",
            component_score=95.0,
            weight=0.15,
            reason="Critical deployment dependencies are currently reachable.",
            raw_payload={
                "dns_ok": True,
                "registry_ok": True,
            },
        )

        db.commit()
        print("Sample score run inserted successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

from observatory.database import SessionLocal, init_platform_db
from observatory.demo_data import reset_demo_workspace, seed_demo_workspace
from observatory.models import AlertRule, EvaluationResult, Incident, LlmCall, Project


def test_seed_demo_workspace_creates_customer_demo_data() -> None:
    init_platform_db()
    with SessionLocal() as session:
        result = seed_demo_workspace(session)
        assert result["organization_id"]
        assert result["project_id"]

        assert session.query(Project).filter_by(organization_id=result["organization_id"]).count() >= 1
        assert session.query(LlmCall).filter_by(organization_id=result["organization_id"]).count() >= 6
        assert session.query(EvaluationResult).filter_by(organization_id=result["organization_id"]).count() >= 6
        assert session.query(AlertRule).filter_by(organization_id=result["organization_id"]).count() >= 1
        assert session.query(Incident).filter_by(organization_id=result["organization_id"]).count() >= 1

        deleted = reset_demo_workspace(session)
        assert deleted > 0
        assert session.query(Project).filter_by(organization_id=result["organization_id"]).count() == 0

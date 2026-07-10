from app.api.routes.health import health


def test_health_contract_shape() -> None:
    response = health()

    assert response.status == "ok"
    assert response.service == "api"
    assert response.version
    assert response.time is not None

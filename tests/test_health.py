import pytest


@pytest.mark.django_db
def test_health_is_public_and_checks_the_database(api_client):
    response = api_client.get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] in {"postgresql", "sqlite"}


@pytest.mark.django_db
def test_openapi_schema_is_generated(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200
    assert b"Clinic Appointments API" in response.content

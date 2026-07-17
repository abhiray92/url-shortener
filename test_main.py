import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False},
    )
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    main.Base.metadata.create_all(bind=test_engine)

    db = main.SessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    main.app.dependency_overrides[main.get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    db.close()
    main.Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_shorten_valid_url(client: TestClient):
    response = client.post("/shorten", json={"long_url": "https://github.com"})

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["short_code"], str)
    assert payload["short_code"]


def test_shorten_invalid_url(client: TestClient):
    response = client.post("/shorten", json={"long_url": "not-a-url"})

    assert response.status_code == 400


def test_shorten_same_url_twice(client: TestClient):
    long_url = "https://example.com"

    first_response = client.post("/shorten", json={"long_url": long_url})
    second_response = client.post("/shorten", json={"long_url": long_url})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["short_code"] == second_response.json()["short_code"]


def test_redirect_valid_code(client: TestClient):
    shorten_response = client.post("/shorten", json={"long_url": "https://example.org"})
    short_code = shorten_response.json()["short_code"]

    response = client.get(f"/{short_code}")

    assert response.status_code == 404


def test_redirect_invalid_code(client: TestClient):
    response = client.get("/nonexistent")

    assert response.status_code == 404

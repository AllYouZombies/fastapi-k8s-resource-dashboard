"""Main application tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_redirect():
    """Test root endpoint redirects to dashboard"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/dashboard"


def test_dashboard_loads():
    """Test dashboard page loads"""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_endpoints_exist():
    """Test that API endpoints respond (even if with errors due to missing services)"""
    # These might return errors due to missing Prometheus/K8s, but should not 404
    endpoints = [
        "/api/metrics",
        "/api/chart-data",
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code != 404
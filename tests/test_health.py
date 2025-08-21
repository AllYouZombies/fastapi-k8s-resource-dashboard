"""Health endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_liveness():
    """Test liveness health check"""
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_health_readiness():
    """Test readiness health check"""
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_health_root():
    """Test health root endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "database_status" in data
    assert "kubernetes_status" in data
    assert "prometheus_status" in data
    assert "status" in data
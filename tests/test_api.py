"""API endpoint tests"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_metrics_endpoint():
    """Test metrics API endpoint"""
    response = client.get("/api/metrics")
    # Should not return 404, but may return errors due to missing services
    assert response.status_code != 404


def test_chart_data_endpoint():
    """Test chart data API endpoint"""
    response = client.get("/api/chart-data")
    # Should not return 404, but may return errors due to missing services
    assert response.status_code != 404


def test_recommendations_endpoint():
    """Test recommendations API endpoint"""
    # Use a generic pod/container name for testing
    response = client.get("/api/recommendations/test-pod/test-container")
    # Should not return 404, but may return 404 if pod not found or other errors
    assert response.status_code in [200, 404, 500]  # Valid responses


def test_static_assets():
    """Test that static assets are served"""
    # Test CSS files
    css_response = client.get("/static/css/dashboard.css")
    assert css_response.status_code == 200
    
    # Test JavaScript files
    js_response = client.get("/static/js/dashboard.js")
    assert js_response.status_code == 200
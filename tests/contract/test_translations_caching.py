"""Tests for /translations endpoint HTTP caching headers."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestTranslationsCaching:
    """Tests for HTTP caching headers on /api/mini-app/translations endpoint."""

    def test_translations_endpoint_has_cache_control_header(self, client: TestClient):
        """Verify Cache-Control header is set for cacheability."""
        response = client.get("/api/mini-app/translations")
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "public, max-age=3600"

    def test_translations_endpoint_has_etag_header(self, client: TestClient):
        """Verify ETag header is present for cache validation."""
        response = client.get("/api/mini-app/translations")
        assert response.status_code == 200
        assert "ETag" in response.headers
        # ETag should be in quoted format, e.g., "abc123def456"
        etag = response.headers["ETag"]
        assert etag.startswith('"') and etag.endswith('"')

    def test_translations_endpoint_etag_is_consistent(self, client: TestClient):
        """Verify ETag is consistent across identical requests."""
        response1 = client.get("/api/mini-app/translations")
        response2 = client.get("/api/mini-app/translations")
        assert response1.headers["ETag"] == response2.headers["ETag"]

    def test_translations_endpoint_returns_valid_json(self, client: TestClient):
        """Verify endpoint returns valid JSON translations data."""
        response = client.get("/api/mini-app/translations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should contain translation keys
        assert len(data) > 0

    def test_translations_endpoint_caching_headers_on_success_only(self, client: TestClient):
        """Verify caching headers are set on successful 200 responses."""
        response = client.get("/api/mini-app/translations")
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "ETag" in response.headers

    def test_translations_endpoint_returns_304_with_matching_etag(self, client: TestClient):
        """Verify endpoint returns 304 Not Modified when ETag matches."""
        # First request to get the ETag
        response1 = client.get("/api/mini-app/translations")
        assert response1.status_code == 200
        etag = response1.headers["ETag"]

        # Second request with If-None-Match header
        response2 = client.get("/api/mini-app/translations", headers={"If-None-Match": etag})
        assert response2.status_code == 304
        assert "ETag" in response2.headers
        assert response2.headers["ETag"] == etag

    def test_translations_endpoint_returns_200_with_mismatched_etag(self, client: TestClient):
        """Verify endpoint returns 200 with data when ETag doesn't match."""
        response = client.get(
            "/api/mini-app/translations", headers={"If-None-Match": '"invalid-etag"'}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_translations_endpoint_cache_flow_simulation(self, client: TestClient):
        """Simulate real caching flow: fetch, cache, validate, get 304."""
        # Step 1: Initial fetch (200 with full data)
        fetch1 = client.get("/api/mini-app/translations")
        assert fetch1.status_code == 200
        data = fetch1.json()
        etag = fetch1.headers["ETag"]
        cache_control = fetch1.headers["Cache-Control"]

        # Verify cache headers
        assert "public, max-age=3600" in cache_control
        assert len(data) > 0

        # Step 2: Cached fetch with If-None-Match (304 not modified)
        fetch2 = client.get("/api/mini-app/translations", headers={"If-None-Match": etag})
        assert fetch2.status_code == 304
        assert fetch2.headers["ETag"] == etag
        # 304 response should have no body
        assert len(fetch2.content) == 0

"""
Integration tests for mObywatel service.

These tests verify the integration with the weryfikator service,
particularly token verification and TTL validation.
"""

import os
import time

from fastapi.testclient import TestClient
import httpx
from main import app, get_settings
import pytest


@pytest.fixture
def weryfikator_url():
    """Get the weryfikator service URL from environment or use default."""
    return os.getenv('WERYFIKATOR_URL')


@pytest.fixture
def valid_token(weryfikator_url):
    """Generate a valid token from the weryfikator service."""
    response = httpx.post(
        f'{weryfikator_url}/generate-token',
        json={'domain': 'example.com', 'ttl_seconds': 60}
    )
    assert response.status_code == 201
    return response.json()['token']


@pytest.fixture
def expired_token(weryfikator_url):
    """Generate a token that has already expired."""
    # Generate with TTL of 1 second
    response = httpx.post(
        f'{weryfikator_url}/generate-token',
        json={'domain': 'example.com', 'ttl_seconds': 1}
    )
    assert response.status_code == 201
    token = response.json()['token']
    
    # Wait for token to expire using synchronous httpx
    time.sleep(2)
    return token


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def valid_user_headers():
    """Headers with a valid user ID from USERS_DB."""
    return {'X-User-ID': 'user001'}


class TestTokenVerification:
    """Test token verification integration with weryfikator service."""

    def test_valid_token_passes_verification(self, client, valid_user_headers, valid_token):
        """Test that a valid token from weryfikator passes verification."""
        response = client.post(
            '/verify-token', headers=valid_user_headers, json={'token': valid_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data['valid'] is True
        assert 'verified successfully' in data['message'].lower()
        assert data['domain'] == 'example.com'

    def test_expired_token_fails_verification(self, client, valid_user_headers, expired_token):
        """Test that an expired token is rejected by weryfikator."""
        response = client.post(
            '/verify-token', headers=valid_user_headers, json={'token': expired_token}
        )

        assert response.status_code == 401
        assert 'expired' in response.json()['detail'].lower()

    def test_invalid_token_fails_verification(self, client, valid_user_headers):
        """Test that an invalid token is rejected by weryfikator."""
        # Use a completely invalid token
        invalid_token = 'this_is_not_a_valid_token_at_all'
        
        response = client.post(
            '/verify-token', headers=valid_user_headers, json={'token': invalid_token}
        )

        assert response.status_code == 401
        detail = response.json()['detail'].lower()
        # Could be invalid signature, invalid format, etc.
        assert 'invalid' in detail or 'failed' in detail

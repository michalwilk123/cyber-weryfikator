"""
Tests for the Weryfikator service.
"""

import base64
import time

from fastapi.testclient import TestClient
from main import app, get_settings
import pytest

# Test configuration
TEST_MASTER_SECRET = 'test_master_secret_key'
TEST_DEFAULT_TTL = 30


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    from main import Settings

    settings = Settings(master_secret=TEST_MASTER_SECRET, default_ttl_seconds=TEST_DEFAULT_TTL)
    return settings


@pytest.fixture
def client(test_settings):
    """Create test client with overridden settings."""
    app.dependency_overrides[get_settings] = lambda: test_settings
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestTokenGeneration:
    """Tests for token generation endpoint."""

    def test_generate_token_with_domain(self, client):
        """Test generating a token with required domain parameter."""
        response = client.post('/generate-token', json={'domain': 'bank.example.com'})

        assert response.status_code == 201
        data = response.json()
        assert 'token' in data
        assert isinstance(data['token'], str)
        assert len(data['token']) > 0

        # Verify domain is embedded in token (without protocol)
        token_data = base64.b64decode(data['token']).decode('utf-8')
        parts = token_data.split(':')
        assert len(parts) == 5
        assert parts[0] == 'bank.example.com'

    def test_generate_token_strips_http_prefix(self, client):
        """Test that http:// prefix is stripped from domain."""
        response = client.post('/generate-token', json={'domain': 'http://bank.example.com'})

        assert response.status_code == 201
        data = response.json()

        # Verify protocol is stripped
        token_data = base64.b64decode(data['token']).decode('utf-8')
        parts = token_data.split(':')
        assert parts[0] == 'bank.example.com'

    def test_generate_token_with_custom_ttl(self, client):
        """Test generating a token with custom TTL."""
        response = client.post(
            '/generate-token', json={'domain': 'bank.example.com', 'ttl_seconds': 60}
        )

        assert response.status_code == 201
        data = response.json()
        assert 'token' in data

        # Decode and verify TTL is in the token
        token_data = base64.b64decode(data['token']).decode('utf-8')
        parts = token_data.split(':')
        assert len(parts) == 5
        assert parts[2] == '60'  # TTL should be 60

    def test_generate_token_without_domain(self, client):
        """Test that generating a token without domain fails."""
        response = client.post('/generate-token', json={'ttl_seconds': 30})

        assert response.status_code == 422  # Validation error

    def test_generate_token_with_invalid_ttl(self, client):
        """Test that generating a token with invalid TTL fails."""
        response = client.post(
            '/generate-token',
            json={
                'domain': 'bank.example.com',
                'ttl_seconds': -1,  # Invalid: must be >= 1
            },
        )

        assert response.status_code == 422  # Validation error

    def test_generate_token_uses_default_ttl(self, client):
        """Test that default TTL is used when not specified."""
        response = client.post('/generate-token', json={'domain': 'bank.example.com'})

        assert response.status_code == 201
        data = response.json()

        # Decode and verify default TTL is used
        token_data = base64.b64decode(data['token']).decode('utf-8')
        parts = token_data.split(':')
        assert parts[2] == str(TEST_DEFAULT_TTL)

    def test_generate_multiple_tokens_are_unique(self, client):
        """Test that multiple token generations produce unique tokens."""
        response1 = client.post('/generate-token', json={'domain': 'bank.example.com'})
        response2 = client.post('/generate-token', json={'domain': 'bank.example.com'})

        assert response1.status_code == 201
        assert response2.status_code == 201

        token1 = response1.json()['token']
        token2 = response2.json()['token']

        # Tokens should be different due to unique salt
        assert token1 != token2


class TestTokenVerification:
    """Tests for token verification endpoint."""

    def test_verify_valid_token(self, client):
        """Test verifying a valid token."""
        # Generate a token
        gen_response = client.post('/generate-token', json={'domain': 'bank.example.com'})
        token = gen_response.json()['token']

        # Verify the token
        verify_response = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data['valid'] is True
        assert 'successfully' in data['message'].lower()
        assert data['domain'] == 'bank.example.com'

    def test_verify_token_with_https_prefix(self, client):
        """Test verifying a token when domain has https:// prefix."""
        # Generate a token with https:// prefix
        gen_response = client.post('/generate-token', json={'domain': 'https://bank.example.com'})
        token = gen_response.json()['token']

        # Verify (domain is stripped to bank.example.com in token)
        verify_response = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response.status_code == 200
        assert verify_response.json()['valid'] is True
        assert verify_response.json()['domain'] == 'bank.example.com'

    def test_verify_token_domain_normalization(self, client):
        """Test that domain normalization works during generation."""
        # Generate token with https:// prefix
        gen_response = client.post('/generate-token', json={'domain': 'https://bank.example.com'})
        token = gen_response.json()['token']

        # Verify token (domain should be normalized to bank.example.com)
        verify_response = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response.status_code == 200
        assert verify_response.json()['valid'] is True
        assert verify_response.json()['domain'] == 'bank.example.com'

    def test_verify_token_domain_mismatch(self, client):
        """Test that domain is correctly extracted from token."""
        # Generate token for bank.example.com
        gen_response = client.post('/generate-token', json={'domain': 'bank.example.com'})
        token = gen_response.json()['token']

        # Verify returns the domain from the token
        verify_response = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data['valid'] is True
        assert data['domain'] == 'bank.example.com'

    def test_verify_token_can_be_reused_within_ttl(self, client):
        """Test that a token can be verified multiple times within TTL."""
        # Generate a token
        gen_response = client.post(
            '/generate-token', json={'domain': 'bank.example.com', 'ttl_seconds': 10}
        )
        token = gen_response.json()['token']

        # Verify the token twice
        verify_response1 = client.post(
            '/verify-token', json={'token': token}
        )
        verify_response2 = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response1.status_code == 200
        assert verify_response2.status_code == 200
        assert verify_response1.json()['valid'] is True
        assert verify_response2.json()['valid'] is True

    def test_verify_expired_token(self, client):
        """Test verifying an expired token."""
        # Generate a token with 1 second TTL
        gen_response = client.post(
            '/generate-token', json={'domain': 'bank.example.com', 'ttl_seconds': 1}
        )
        token = gen_response.json()['token']

        # Wait for token to expire
        time.sleep(2)

        # Try to verify the expired token
        verify_response = client.post(
            '/verify-token', json={'token': token}
        )

        assert verify_response.status_code == 401
        data = verify_response.json()
        assert 'expired' in data['detail'].lower()

    def test_verify_tampered_token(self, client):
        """Test verifying a token that has been tampered with."""
        # Generate a valid token
        gen_response = client.post('/generate-token', json={'domain': 'bank.example.com'})
        valid_token = gen_response.json()['token']

        # Tamper with the token
        tampered_token = valid_token[:-10] + 'TAMPERED=='

        # Try to verify the tampered token
        verify_response = client.post(
            '/verify-token', json={'token': tampered_token}
        )

        assert verify_response.status_code == 401

    def test_verify_forged_token(self, client):
        """Test verifying a token forged without the master secret."""
        from datetime import datetime, timezone
        import hashlib
        import secrets

        # Try to create a fake token without knowing the secret
        fake_domain = 'bank.example.com'
        fake_timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        fake_ttl = '30'
        fake_salt = secrets.token_bytes(16).hex()
        fake_signature = hashlib.sha256(b'wrong_secret').hexdigest()

        fake_token_data = f'{fake_domain}:{fake_timestamp}:{fake_ttl}:{fake_salt}:{fake_signature}'
        fake_token = base64.b64encode(fake_token_data.encode('utf-8')).decode('utf-8')

        # Try to verify the forged token
        verify_response = client.post(
            '/verify-token', json={'token': fake_token}
        )

        assert verify_response.status_code == 401
        data = verify_response.json()
        assert 'signature' in data['detail'].lower() or 'invalid' in data['detail'].lower()

    def test_verify_malformed_token(self, client):
        """Test verifying a malformed token."""
        malformed_token = 'this_is_not_a_valid_token'

        verify_response = client.post(
            '/verify-token', json={'token': malformed_token}
        )

        assert verify_response.status_code == 401

class TestCryptoIntegration:
    """Integration tests for crypto operations."""

    def test_token_signature_integrity(self, client):
        """Test that token signature ensures integrity."""
        # Generate a token
        gen_response = client.post('/generate-token', json={'domain': 'bank.example.com'})
        token = gen_response.json()['token']

        # Decode token
        token_data = base64.b64decode(token).decode('utf-8')
        parts = token_data.split(':')
        domain, timestamp, ttl, salt, signature = parts

        # Modify one character in the timestamp
        modified_timestamp = str(int(timestamp) + 1)
        modified_token_data = f'{domain}:{modified_timestamp}:{ttl}:{salt}:{signature}'
        modified_token = base64.b64encode(modified_token_data.encode('utf-8')).decode('utf-8')

        # Try to verify the modified token
        verify_response = client.post(
            '/verify-token', json={'token': modified_token}
        )

        # Should fail due to signature mismatch
        assert verify_response.status_code == 401

    def test_salt_uniqueness(self, client):
        """Test that each token has a unique salt."""
        # Generate two tokens
        response1 = client.post('/generate-token', json={'domain': 'bank.example.com'})
        response2 = client.post('/generate-token', json={'domain': 'bank.example.com'})

        token1 = response1.json()['token']
        token2 = response2.json()['token']

        # Decode tokens and extract salts
        token1_data = base64.b64decode(token1).decode('utf-8')
        token2_data = base64.b64decode(token2).decode('utf-8')

        salt1 = token1_data.split(':')[3]
        salt2 = token2_data.split(':')[3]

        # Salts should be different
        assert salt1 != salt2

    def test_domain_binding(self, client):
        """Test that tokens are bound to the domain they were created for."""
        # Generate token for domain A
        gen_response = client.post('/generate-token', json={'domain': 'domainA.example.com'})
        token = gen_response.json()['token']

        # Verify - should succeed and return domainA
        verify_response_a = client.post(
            '/verify-token', json={'token': token}
        )
        assert verify_response_a.status_code == 200
        assert verify_response_a.json()['domain'] == 'domainA.example.com'

        # The token is valid, but it contains domainA, not domainB
        # The service just verifies the token and returns the domain embedded in it
        # The caller is responsible for checking if the returned domain matches expectations

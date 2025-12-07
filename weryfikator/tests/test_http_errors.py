"""
Tests for HTTP security checks.
"""

import pytest
import pytest_asyncio
import aiohttp
from checks.http_errors import check_insecure_http, _check_http_redirects
from checks.base import HTTPError


@pytest_asyncio.fixture
async def session():
    """Create aiohttp session for tests."""
    async with aiohttp.ClientSession() as s:
        yield s


class TestCheckInsecureHTTP:
    """Tests for check_insecure_http function."""
    
    @pytest.mark.asyncio
    async def test_http_only_domain(self, session):
        """Test that a domain only accepting HTTP raises HTTPError."""
        # Note: Finding reliable HTTP-only domains in 2025 is difficult
        # Most sites have moved to HTTPS. This test uses neverssl.com
        # which is specifically designed to only work over HTTP
        with pytest.raises(HTTPError) as exc_info:
            await check_insecure_http(session, "http.badssl.com", timeout=5)
        
        assert "only accepts insecure HTTP" in str(exc_info.value).lower() or \
               "insecure http" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_https_with_valid_cert(self, session):
        """Test domain with valid HTTPS certificate."""
        # badssl.com itself has valid HTTPS
        result = await check_insecure_http(session, "badssl.com")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_expired_cert_falls_back_to_http(self, session):
        """Test that expired cert domains are flagged as unreachable."""
        # expired.badssl.com has an expired certificate and doesn't accept HTTP
        # Should raise HTTPError indicating the domain is unreachable
        with pytest.raises(HTTPError) as exc_info:
            await check_insecure_http(session, "expired.badssl.com", timeout=5)
        
        assert "unreachable" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_self_signed_cert_no_http_fallback(self, session):
        """Test that self-signed cert domains are handled correctly."""
        # self-signed.badssl.com has a self-signed certificate
        # It likely doesn't accept HTTP, so should be marked unreachable
        with pytest.raises(HTTPError):
            await check_insecure_http(session, "self-signed.badssl.com", timeout=5)


class TestCheckHTTPRedirects:
    """Tests for _check_http_redirects function."""
    
    @pytest.mark.asyncio
    async def test_no_redirect_to_http(self, session):
        """Test that HTTPS sites without HTTP redirects pass."""
        async with session.get("https://www.google.com") as response:
            await response.read()
            # Should not raise
            _check_http_redirects(response, "https://www.google.com")

class TestHTTPSecurityIntegration:
    """Integration tests for HTTP security checks."""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, session):
        """Test that timeout is properly handled."""
        # Using a very short timeout on a slow-responding domain
        with pytest.raises(HTTPError) as exc_info:
            await check_insecure_http(session, "httpbin.org", timeout=0.001)
        
        assert "unreachable" in str(exc_info.value).lower()


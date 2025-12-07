"""
Tests for SSL/Certificate and HTTP security checks.
"""

import pytest
import pytest_asyncio
import aiohttp
from checks.ssl_errors import check_url_security
from checks.base import CertificateError, HTTPError


@pytest_asyncio.fixture
async def session():
    """Create an aiohttp session for testing."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.mark.asyncio
async def test_expired_certificate(session):
    """Test detection of expired SSL certificate."""
    with pytest.raises(CertificateError, match="expired"):
        await check_url_security(session, "https://expired.badssl.com/")


@pytest.mark.asyncio
async def test_wrong_host(session):
    """Test detection of certificate hostname mismatch."""
    with pytest.raises(CertificateError, match="hostname|mismatch"):
        await check_url_security(session, "https://wrong.host.badssl.com/")


@pytest.mark.asyncio
async def test_self_signed_certificate(session):
    """Test detection of self-signed certificate."""
    with pytest.raises(CertificateError, match="self-signed|Self-signed"):
        await check_url_security(session, "https://self-signed.badssl.com/")


@pytest.mark.asyncio
async def test_untrusted_root(session):
    """Test detection of untrusted root certificate."""
    with pytest.raises(CertificateError, match="[Uu]ntrusted|certificate"):
        await check_url_security(session, "https://untrusted-root.badssl.com/")


@pytest.mark.asyncio
async def test_http_insecure(session):
    """Test detection of plain HTTP connection."""
    with pytest.raises(HTTPError, match="[Ii]nsecure|HTTP"):
        await check_url_security(session, "http://http.badssl.com/")


@pytest.mark.asyncio
async def test_valid_certificate(session):
    """Test that valid certificates pass the check."""
    # badssl.com itself has a valid certificate
    result = await check_url_security(session, "https://badssl.com/")
    assert result is True



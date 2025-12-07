"""
Comprehensive tests for the unified security check function.

This test suite ensures that check_domain_security() properly:
1. Validates domains against whitelist
2. Detects SSL/certificate issues
3. Detects key exchange vulnerabilities
4. Detects HTTP security issues
5. Uses minimal network requests (max 2)
"""

import pytest
import pytest_asyncio
import aiohttp
from checks import (
    check_domain_security,
    DomainError,
    CertificateError,
    KeyExchangeError,
    HTTPError,
)


@pytest_asyncio.fixture
async def session():
    """Create aiohttp session for tests."""
    async with aiohttp.ClientSession() as s:
        yield s


class TestDomainWhitelist:
    """Tests for domain whitelist validation."""
    
    @pytest.mark.asyncio
    async def test_valid_government_domain(self, session):
        """Test that a valid government domain passes whitelist check."""
        # arimr.gov.pl is in the list
        # Note: We skip domain check here since it may not have valid HTTPS
        # This tests the whitelist logic
        try:
            await check_domain_security(session, "arimr.gov.pl", timeout=10)
        except (CertificateError, KeyExchangeError, HTTPError):
            # Expected - domain might have security issues
            # But should NOT raise DomainError
            pass
    
    @pytest.mark.asyncio
    async def test_invalid_domain_rejected(self, session):
        """Test that a non-whitelisted domain raises DomainError."""
        with pytest.raises(DomainError, match="not in the government domains list"):
            await check_domain_security(session, "fake-domain.gov.pl")
    
    @pytest.mark.asyncio
    async def test_skip_whitelist_check(self, session):
        """Test that whitelist can be skipped with flag."""
        # Should not raise DomainError even for non-whitelisted domain
        # (but will likely raise other errors since badssl.com isn't whitelisted)
        try:
            result = await check_domain_security(
                session, 
                "badssl.com", 
                skip_domain_whitelist=True,
                timeout=5
            )
            assert result is True
        except (CertificateError, KeyExchangeError, HTTPError):
            # These are ok - we're just testing that DomainError isn't raised
            pass


class TestCertificateValidation:
    """Tests for SSL/Certificate validation through unified function."""
    
    @pytest.mark.asyncio
    async def test_expired_certificate_detected(self, session):
        """Test that expired certificates are detected."""
        with pytest.raises(CertificateError, match="expired"):
            await check_domain_security(
                session, 
                "expired.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
    
    @pytest.mark.asyncio
    async def test_wrong_hostname_detected(self, session):
        """Test that hostname mismatch is detected."""
        with pytest.raises(CertificateError, match="hostname|mismatch"):
            await check_domain_security(
                session,
                "wrong.host.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
    
    @pytest.mark.asyncio
    async def test_self_signed_certificate_detected(self, session):
        """Test that self-signed certificates are detected."""
        with pytest.raises(CertificateError, match="[Ss]elf-signed"):
            await check_domain_security(
                session,
                "self-signed.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
    
    @pytest.mark.asyncio
    async def test_untrusted_root_detected(self, session):
        """Test that untrusted root certificates are detected."""
        with pytest.raises(CertificateError, match="[Uu]ntrusted|certificate"):
            await check_domain_security(
                session,
                "untrusted-root.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )


class TestKeyExchangeSecurity:
    """Tests for key exchange validation through unified function."""
    
    @pytest.mark.asyncio
    async def test_weak_dh480_detected(self, session):
        """Test that DH-480 is detected as weak."""
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_domain_security(
                session,
                "dh480.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "dh" in error_msg or "key" in error_msg
    
    @pytest.mark.asyncio
    async def test_weak_dh512_detected(self, session):
        """Test that DH-512 is detected as weak."""
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_domain_security(
                session,
                "dh512.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "dh" in error_msg or "key" in error_msg
    
    @pytest.mark.asyncio
    async def test_weak_dh1024_detected(self, session):
        """Test that DH-1024 is detected as weak."""
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_domain_security(
                session,
                "dh1024.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "dh" in error_msg or "key" in error_msg
    
    @pytest.mark.asyncio
    async def test_dh2048_acceptable(self, session):
        """Test that DH-2048 is acceptable."""
        try:
            result = await check_domain_security(
                session,
                "dh2048.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
            assert result is True
        except Exception as e:
            # Only KeyExchangeError would indicate failure
            assert not isinstance(e, KeyExchangeError), \
                f"DH-2048 should be acceptable: {e}"


class TestHTTPSecurity:
    """Tests for HTTP security through unified function."""
    
    @pytest.mark.asyncio
    async def test_http_only_domain_detected(self, session):
        """Test that HTTP-only domains are detected."""
        with pytest.raises(HTTPError) as exc_info:
            await check_domain_security(
                session,
                "http.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        error_msg = str(exc_info.value).lower()
        assert "http" in error_msg or "insecure" in error_msg


class TestValidDomains:
    """Tests for domains that should pass all security checks."""
    
    @pytest.mark.asyncio
    async def test_valid_modern_domain(self, session):
        """Test that a secure modern domain passes all checks."""
        result = await check_domain_security(
            session,
            "badssl.com",
            skip_domain_whitelist=True,
            timeout=5
        )
        assert result is True
    
    @pytest.mark.asyncio
    async def test_google_passes(self, session):
        """Test that Google.com passes all security checks."""
        result = await check_domain_security(
            session,
            "google.com",
            skip_domain_whitelist=True,
            timeout=5
        )
        assert result is True


class TestErrorPriority:
    """Tests for error detection priority and delegation."""
    
    @pytest.mark.asyncio
    async def test_certificate_error_before_key_exchange(self, session):
        """Test that certificate errors are detected over key exchange errors."""
        # self-signed.badssl.com has a certificate issue
        # Should raise CertificateError, not KeyExchangeError
        with pytest.raises(CertificateError):
            await check_domain_security(
                session,
                "self-signed.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
    
    @pytest.mark.asyncio
    async def test_key_exchange_error_properly_delegated(self, session):
        """Test that key exchange errors are properly identified."""
        # dh480.badssl.com specifically has key exchange issues
        # Should raise KeyExchangeError
        with pytest.raises(KeyExchangeError):
            await check_domain_security(
                session,
                "dh480.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )


class TestNetworkEfficiency:
    """Tests to verify minimal network requests are made."""
    
    @pytest.mark.asyncio
    async def test_single_request_for_valid_domain(self, session):
        """Test that only one request is made for valid HTTPS domains."""
        # This is difficult to test directly without mocking,
        # but we verify the function completes efficiently
        import time
        start = time.time()
        
        result = await check_domain_security(
            session,
            "badssl.com",
            skip_domain_whitelist=True,
            timeout=5
        )
        
        elapsed = time.time() - start
        assert result is True
        # Should complete quickly (< 2 seconds for one request)
        assert elapsed < 2.0
    
    @pytest.mark.asyncio
    async def test_single_request_for_cert_error(self, session):
        """Test that only one request is made when certificate error occurs."""
        import time
        start = time.time()
        
        with pytest.raises(CertificateError):
            await check_domain_security(
                session,
                "expired.badssl.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        elapsed = time.time() - start
        # Should complete quickly (< 2 seconds for one request)
        assert elapsed < 2.0


class TestTimeout:
    """Tests for timeout handling."""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, session):
        """Test that timeouts are properly handled."""
        # Using extremely short timeout
        with pytest.raises((HTTPError, Exception)):
            await check_domain_security(
                session,
                "badssl.com",
                skip_domain_whitelist=True,
                timeout=0.001
            )


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_nonexistent_domain(self, session):
        """Test handling of non-existent domains."""
        with pytest.raises(HTTPError) as exc_info:
            await check_domain_security(
                session,
                "this-domain-definitely-does-not-exist-12345.com",
                skip_domain_whitelist=True,
                timeout=5
            )
        
        # Should raise HTTPError with "unreachable" message
        assert "unreachable" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_domain_with_port(self, session):
        """Test that domains with ports are handled."""
        # Even though we don't typically use ports, function should handle it
        try:
            await check_domain_security(
                session,
                "badssl.com:443",
                skip_domain_whitelist=True,
                timeout=5
            )
        except DomainError:
            # Expected if whitelist doesn't include port notation
            pass


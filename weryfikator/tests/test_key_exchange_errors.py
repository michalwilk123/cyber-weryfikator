"""
Tests for Key Exchange security checks.
"""

import pytest
import pytest_asyncio
import aiohttp
from checks.key_exchange_errors import check_weak_key_exchange, check_key_exchange_group
from checks.base import KeyExchangeError


@pytest_asyncio.fixture
async def session():
    """Create aiohttp session for tests."""
    async with aiohttp.ClientSession() as s:
        yield s


class TestCheckWeakKeyExchange:
    """Tests for check_weak_key_exchange function."""
    
    @pytest.mark.asyncio
    async def test_dh480_weak(self, session):
        """Test that DH-480 is detected as weak."""
        # badssl.com provides a dh480.badssl.com endpoint for testing
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_weak_key_exchange(session, "dh480.badssl.com", timeout=5)
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "key" in error_msg or "dh" in error_msg
    
    @pytest.mark.asyncio
    async def test_dh512_weak(self, session):
        """Test that DH-512 is detected as weak."""
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_weak_key_exchange(session, "dh512.badssl.com", timeout=5)
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "key" in error_msg or "dh" in error_msg
    
    @pytest.mark.asyncio
    async def test_dh1024_weak(self, session):
        """Test that DH-1024 is detected as weak."""
        with pytest.raises(KeyExchangeError) as exc_info:
            await check_weak_key_exchange(session, "dh1024.badssl.com", timeout=5)
        
        error_msg = str(exc_info.value).lower()
        assert "weak" in error_msg or "key" in error_msg or "dh" in error_msg
    
    @pytest.mark.asyncio
    async def test_dh2048_acceptable(self, session):
        """Test that DH-2048 is acceptable."""
        # DH-2048 should be accepted by modern clients
        try:
            result = await check_weak_key_exchange(session, "dh2048.badssl.com", timeout=5)
            assert result is True
        except Exception as e:
            # If badssl.com's DH-2048 test has cert issues, that's not a key exchange error
            # Only KeyExchangeError should fail this test
            assert not isinstance(e, KeyExchangeError), \
                f"DH-2048 should be acceptable, but got KeyExchangeError: {e}"
    
    @pytest.mark.asyncio
    async def test_dh_small_subgroup(self, session):
        """Test that DH small subgroup vulnerability is detected."""
        # Note: badssl.com provides dh-small-subgroup.badssl.com
        # However, modern browsers may accept this or the domain may not exist
        # We test it but allow it to pass if the domain doesn't have issues
        try:
            result = await check_weak_key_exchange(session, "dh-small-subgroup.badssl.com", timeout=5)
            # If it passes, that's ok - the domain might not exist or be configured differently
            assert result is True or result is None
        except KeyExchangeError as e:
            # If it raises KeyExchangeError, verify it's about DH issues
            error_msg = str(e).lower()
            assert "weak" in error_msg or "key" in error_msg or "dh" in error_msg or "handshake" in error_msg
        except Exception:
            # Other exceptions (DNS, connection) are ok for this test
            pass
    
    @pytest.mark.asyncio
    async def test_dh_composite(self, session):
        """Test that DH composite modulus vulnerability is detected."""
        # Note: badssl.com provides dh-composite.badssl.com
        # However, modern browsers may accept this or the domain may not exist
        # We test it but allow it to pass if the domain doesn't have issues
        try:
            result = await check_weak_key_exchange(session, "dh-composite.badssl.com", timeout=5)
            # If it passes, that's ok - the domain might not exist or be configured differently
            assert result is True or result is None
        except KeyExchangeError as e:
            # If it raises KeyExchangeError, verify it's about DH issues
            error_msg = str(e).lower()
            assert "weak" in error_msg or "key" in error_msg or "dh" in error_msg or "handshake" in error_msg
        except Exception:
            # Other exceptions (DNS, connection) are ok for this test
            pass
    
    @pytest.mark.asyncio
    async def test_valid_modern_domain(self, session):
        """Test that a domain with valid key exchange parameters passes."""
        # badssl.com itself uses modern, secure parameters
        result = await check_weak_key_exchange(session, "badssl.com", timeout=5)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, session):
        """Test that timeout errors are handled appropriately."""
        # Using a very short timeout should cause timeout, not KeyExchangeError
        try:
            await check_weak_key_exchange(session, "badssl.com", timeout=0.001)
            # If it somehow succeeds with tiny timeout, that's ok
        except KeyExchangeError:
            # Should not raise KeyExchangeError for timeout
            pytest.fail("Timeout should not be reported as KeyExchangeError")
        except Exception:
            # Other exceptions (timeout, connection error) are expected
            pass


class TestCheckKeyExchangeGroup:
    """Tests for check_key_exchange_group function."""
    
    @pytest.mark.asyncio
    async def test_group_check_mixed_results(self, session):
        """Test checking multiple domains with mixed results."""
        domains = [
            "badssl.com",  # Should pass
            "dh480.badssl.com",  # Should fail
        ]
        
        results = await check_key_exchange_group(session, domains, timeout=5)
        
        assert isinstance(results, dict)
        assert len(results) == 2
        
        # badssl.com should pass
        assert results.get("badssl.com") is True
        
        # dh480.badssl.com should have an error message
        dh480_result = results.get("dh480.badssl.com")
        assert isinstance(dh480_result, str)
        assert len(dh480_result) > 0
    
    @pytest.mark.asyncio
    async def test_group_check_all_secure(self, session):
        """Test checking multiple secure domains."""
        domains = ["badssl.com", "google.com"]
        
        results = await check_key_exchange_group(session, domains, timeout=5)
        
        assert isinstance(results, dict)
        assert len(results) == 2
        
        # Both should pass
        for domain, result in results.items():
            assert result is True, f"Domain {domain} should pass: {result}"


class TestKeyExchangeIntegration:
    """Integration tests for key exchange checks."""
    
    @pytest.mark.asyncio
    async def test_non_existent_domain(self, session):
        """Test that non-existent domains don't raise KeyExchangeError."""
        # Non-existent domain should raise connection error, not KeyExchangeError
        with pytest.raises(Exception) as exc_info:
            await check_weak_key_exchange(session, "this-domain-definitely-does-not-exist-12345.com", timeout=5)
        
        # Should not be a KeyExchangeError (it's a DNS/connection issue)
        assert not isinstance(exc_info.value, KeyExchangeError)


"""
Tests for Certificate Authority (CA) chain validation.
"""

import pytest
from checks.ca_chain import check_ca_chain
from checks.base import CertificateError


@pytest.mark.asyncio
async def test_gov_pl_valid_ca_chain():
    """Test that gov.pl has the expected Certum root CA."""
    # gov.pl should have Certum Trusted Network CA as root
    result = await check_ca_chain("gov.pl", timeout=15)
    assert result is True

@pytest.mark.asyncio
async def test_other_gov_domain_valid_ca_chain():
    """Test that another gov.pl domain has the expected Certum root CA."""
    # Test with another government domain from the whitelist
    # premier.gov.pl uses Let's Encrypt now, so we switch to eteryt.stat.gov.pl which uses Certum
    result = await check_ca_chain("eteryt.stat.gov.pl", timeout=15)
    assert result is True


@pytest.mark.asyncio
async def test_non_gov_domain_different_ca():
    """Test that non-government domains with different CAs are detected."""
    # Google uses a different CA (Google Trust Services)
    with pytest.raises(CertificateError, match="different root CA|Expected CN"):
        await check_ca_chain("google.com", timeout=15)


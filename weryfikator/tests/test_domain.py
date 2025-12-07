import pytest
from checks.domain import verify_domain
from checks.base import DomainError


def test_verify_domain_exists():
    """Test that a valid government domain passes verification."""
    # arimr.gov.pl is in the list (line 30 of lista_gov_pl_z_www.txt)
    assert verify_domain("arimr.gov.pl") is True


def test_verify_domain_does_not_exist():
    """Test that an invalid domain raises DomainError."""
    with pytest.raises(DomainError, match="Domain 'fake-domain.gov.pl' is not in the government domains list"):
        verify_domain("fake-domain.gov.pl")


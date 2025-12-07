from pathlib import Path
from .base import DomainError

# Load domains once at module import time
_DATA_FILE = Path("checks") / "data" / "lista_gov_pl_z_www.txt"
_GOV_DOMAINS: frozenset[str] = frozenset(
    line.strip() for line in _DATA_FILE.read_text().splitlines() if line.strip()
)

def verify_domain(domain: str) -> bool:
    """
    Verify if the domain is in the government domains list.
    
    Raises:
        DomainError: If the domain is not in the allowed list.
    """
    if domain not in _GOV_DOMAINS:
        raise DomainError(f"Domain '{domain}' is not in the government domains list")
    return True


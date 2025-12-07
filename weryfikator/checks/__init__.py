"""
Security checks module for domain verification.

This module provides comprehensive security checks for domains including:
- Domain whitelist validation
- SSL/Certificate validation
- Key exchange security
- HTTP security

Main entry point:
    check_domain_security() - Unified function that performs all checks with minimal requests
"""

from .base import BaseCheckError, CertificateError, DomainError, HTTPError, KeyExchangeError
from .unified import check_domain_security

__all__ = [
    # Main unified function
    "check_domain_security",
    # Exception classes
    "BaseCheckError",
    "CertificateError",
    "DomainError",
    "HTTPError",
    "KeyExchangeError",
]


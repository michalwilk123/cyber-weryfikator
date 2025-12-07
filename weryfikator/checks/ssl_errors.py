"""
SSL/Certificate and HTTP security checks.

This module provides async functions to check SSL/certificate issues and HTTP security
problems by testing URLs. All checks accept an aiohttp.ClientSession from a connection pool.
"""

import aiohttp
from .base import CertificateError, HTTPError
from .http_errors import _check_http_redirects


def _parse_ssl_error(error: Exception, url: str) -> None:
    """Parse SSL/certificate error and raise appropriate CertificateError."""
    error_msg = str(error).lower()
    
    if "certificate has expired" in error_msg or "expired" in error_msg:
        raise CertificateError(f"Certificate has expired for {url}")
    elif "hostname" in error_msg or "does not match" in error_msg:
        raise CertificateError(f"Certificate hostname mismatch for {url}")
    elif "self signed" in error_msg or "self-signed" in error_msg:
        raise CertificateError(f"Self-signed certificate detected for {url}")
    elif "unable to get local issuer" in error_msg or "certificate verify failed" in error_msg:
        raise CertificateError(f"Untrusted root certificate for {url}")
    else:
        raise CertificateError(f"Certificate error for {url}: {str(error)}")


async def check_url_security(session: aiohttp.ClientSession, url: str, timeout: int = 10) -> bool:
    """
    Comprehensive security check for a URL - checks both SSL/certificate issues and HTTP redirects.
    
    This function detects:
    - SSL/Certificate issues:
      * Expired certificates
      * Hostname mismatch
      * Self-signed certificates
      * Untrusted root certificates
    - HTTP security issues:
      * Plain HTTP connections
      * HTTPS to HTTP redirects (downgrade attacks)
    
    Note: Certificate revocation checking (OCSP/CRL) is not performed as it's not
    enabled by default in Python/OpenSSL and is system-dependent.
    
    Args:
        session: aiohttp ClientSession from connection pool
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        True if URL is secure (valid certificate and no insecure redirects)
        
    Raises:
        CertificateError: If any SSL/certificate issue is detected
        HTTPError: If URL uses HTTP or redirects to HTTP
    """
    # First check if URL is plain HTTP
    if url.startswith("http://"):
        raise HTTPError(f"Insecure HTTP connection for {url}")
    
    try:
        async with session.get(
            url, 
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True
        ) as response:
            await response.read()
            
            # Check for HTTP redirects
            _check_http_redirects(response, url)
            
            return True
            
    except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientSSLError) as e:
        _parse_ssl_error(e, url)
    except (CertificateError, HTTPError):
        raise
    except Exception as e:
        raise HTTPError(f"Security check failed for {url}: {str(e)}")



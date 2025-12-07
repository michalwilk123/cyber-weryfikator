"""
HTTP security checks.

This module provides async functions to check for insecure HTTP usage and HTTP-related
security issues. All checks accept an aiohttp.ClientSession from a connection pool.
"""

import aiohttp
from .base import HTTPError


def _check_http_redirects(response: aiohttp.ClientResponse, original_url: str) -> None:
    """Check response for insecure HTTP redirects."""
    # Check if final URL is HTTP
    if str(response.url).startswith("http://"):
        raise HTTPError(f"Site redirects to insecure HTTP: {original_url} -> {response.url}")
    
    # Check redirect history for any HTTP URLs
    if hasattr(response, 'history'):
        for redirect in response.history:
            if str(redirect.url).startswith("http://"):
                raise HTTPError(f"Redirect chain contains insecure HTTP: {redirect.url}")


async def check_insecure_http(session: aiohttp.ClientSession, domain: str, timeout: int = 10) -> bool:
    """
    Check if a domain only accepts insecure HTTP connections (no HTTPS support).
    
    This function detects domains that are vulnerable to man-in-the-middle attacks
    because they only support plain HTTP without HTTPS encryption.
    
    The check works as follows:
    1. First attempts HTTPS connection (https://domain)
    2. If HTTPS succeeds, the domain is secure (returns True)
    3. If HTTPS fails, attempts HTTP connection (http://domain)
    4. If HTTP succeeds but HTTPS failed, raises HTTPError (insecure HTTP only)
    5. If both fail, raises HTTPError with connection failure details
    
    Args:
        session: aiohttp ClientSession from connection pool
        domain: Plain domain name without protocol (e.g., 'example.com')
        timeout: Request timeout in seconds
        
    Returns:
        True if domain supports HTTPS (secure)
        
    Raises:
        HTTPError: If domain only accepts HTTP or both protocols fail
    """
    https_url = f"https://{domain}"
    http_url = f"http://{domain}"
    
    https_error = None
    http_error = None
    
    # First, try HTTPS
    try:
        async with session.get(
            https_url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
            ssl=True
        ) as response:
            await response.read()
            
            # Check if we were redirected to HTTP (downgrade attack)
            if str(response.url).startswith("http://"):
                raise HTTPError(
                    f"Domain {domain} redirects HTTPS to insecure HTTP: {https_url} -> {response.url}"
                )
            
            # Check redirect history for any HTTP URLs
            if hasattr(response, 'history'):
                for redirect in response.history:
                    if str(redirect.url).startswith("http://"):
                        raise HTTPError(
                            f"Domain {domain} has insecure HTTP in redirect chain: {redirect.url}"
                        )
            
            # HTTPS works properly - domain is secure
            return True
    except HTTPError:
        # Re-raise our HTTPError about redirects
        raise
    except Exception as e:
        https_error = e
    
    # HTTPS failed, now try HTTP
    try:
        async with session.get(
            http_url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True
        ) as response:
            await response.read()
            # HTTP works but HTTPS failed - this is the security issue
            raise HTTPError(
                f"Domain {domain} only accepts insecure HTTP connections. "
                f"HTTPS failed with: {str(https_error)}"
            )
    except HTTPError:
        # Re-raise our HTTPError about insecure HTTP
        raise
    except Exception as e:
        http_error = e
    
    # Both HTTPS and HTTP failed
    raise HTTPError(
        f"Domain {domain} is unreachable. "
        f"HTTPS error: {str(https_error)}. HTTP error: {str(http_error)}"
    )


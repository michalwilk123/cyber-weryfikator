"""
Key Exchange security checks.

This module provides async functions to check for weak Diffie-Hellman key exchange
parameters and other key exchange vulnerabilities. All checks accept an aiohttp.ClientSession
from a connection pool.
"""

import aiohttp
from .base import KeyExchangeError


def _parse_key_exchange_error(error: Exception, domain: str) -> None:
    """Parse key exchange error and raise appropriate KeyExchangeError."""
    error_msg = str(error).lower()
    
    # Check for bad DH value (weak DH parameters)
    if "bad_dh_value" in error_msg or "bad dh value" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} uses invalid or weak Diffie-Hellman parameters (bad DH value). "
            f"This is vulnerable to attacks and rejected by modern clients."
        )
    
    # Check for weak DH key sizes
    if "dh key too small" in error_msg or "dh_key_too_small" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} uses weak Diffie-Hellman key exchange parameters (key too small). "
            f"This is vulnerable to attacks and rejected by modern clients."
        )
    
    # Check for SSL handshake failures that might indicate weak DH
    if "handshake failure" in error_msg or "handshake_failure" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} SSL handshake failed, possibly due to weak key exchange parameters. "
            f"Error: {str(error)}"
        )
    
    # Check for small subgroup attacks
    if "small" in error_msg and "subgroup" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} uses Diffie-Hellman parameters vulnerable to small subgroup attacks."
        )
    
    # Check for composite modulus vulnerabilities
    if "composite" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} uses Diffie-Hellman parameters with composite modulus (vulnerable)."
        )
    
    # Generic SSL/TLS version or cipher suite issues that might relate to key exchange
    if "ssl" in error_msg or "tls" in error_msg or "cipher" in error_msg:
        raise KeyExchangeError(
            f"Domain {domain} has key exchange or cipher suite issues: {str(error)}"
        )
    
    # If we can't categorize it, raise generic error
    raise KeyExchangeError(
        f"Domain {domain} has a key exchange related error: {str(error)}"
    )


async def check_weak_key_exchange(
    session: aiohttp.ClientSession, 
    domain: str, 
    timeout: int = 10
) -> bool:
    """
    Check if a domain uses weak Diffie-Hellman key exchange parameters.
    
    This function detects domains that are vulnerable to attacks due to weak
    Diffie-Hellman parameters in their SSL/TLS configuration:
    
    Detected issues:
    - Weak DH key sizes (480, 512, 1024 bits) - rejected by modern OpenSSL
    - DH small subgroup attacks
    - DH composite modulus vulnerabilities
    
    Acceptable:
    - DH 2048 bits or stronger
    
    The check works by attempting an HTTPS connection. Modern SSL/TLS libraries
    (like OpenSSL) will reject connections with weak DH parameters during the
    handshake, producing specific error messages that we parse.
    
    Args:
        session: aiohttp ClientSession from connection pool
        domain: Plain domain name without protocol (e.g., 'example.com')
        timeout: Request timeout in seconds
        
    Returns:
        True if domain uses secure key exchange parameters
        
    Raises:
        KeyExchangeError: If domain uses weak DH parameters or has key exchange issues
    """
    url = f"https://{domain}"
    
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
            ssl=True
        ) as response:
            await response.read()
            # Connection succeeded - key exchange parameters are acceptable
            return True
            
    except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientConnectorSSLError, aiohttp.ClientSSLError) as e:
        # SSL/Certificate errors might indicate key exchange issues
        # Parse the error to determine if it's key exchange related
        error_msg = str(e).lower()
        
        # Check if this is a key exchange issue
        key_exchange_indicators = [
            "bad_dh_value",
            "bad dh value",
            "dh key too small",
            "dh_key_too_small", 
            "handshake failure",
            "handshake_failure",
            "no shared cipher",
            "cipher",
            "key exchange"
        ]
        
        if any(indicator in error_msg for indicator in key_exchange_indicators):
            _parse_key_exchange_error(e, domain)
        
        # If it's not a key exchange issue, re-raise the original error
        # (it's probably a certificate issue that should be handled elsewhere)
        raise
        
    except KeyExchangeError:
        # Re-raise our KeyExchangeError
        raise
    except Exception as e:
        # Other connection errors (timeout, DNS, etc.) - not key exchange related
        raise


async def check_key_exchange_group(
    session: aiohttp.ClientSession,
    domains: list[str],
    timeout: int = 10
) -> dict[str, bool | str]:
    """
    Check multiple domains for weak key exchange parameters in parallel.
    
    This is a convenience function for checking multiple domains efficiently.
    
    Args:
        session: aiohttp ClientSession from connection pool
        domains: List of domain names to check
        timeout: Request timeout in seconds per domain
        
    Returns:
        Dictionary mapping domain to result:
        - True if secure
        - Error message string if insecure or failed
        
    Example:
        >>> results = await check_key_exchange_group(session, ['example.com', 'test.com'])
        >>> results
        {'example.com': True, 'test.com': 'Domain uses weak DH...'}
    """
    import asyncio
    
    async def check_one(domain: str) -> tuple[str, bool | str]:
        try:
            result = await check_weak_key_exchange(session, domain, timeout)
            return (domain, result)
        except KeyExchangeError as e:
            return (domain, str(e))
        except Exception as e:
            return (domain, f"Check failed: {str(e)}")
    
    # Run checks in parallel
    results = await asyncio.gather(*[check_one(d) for d in domains])
    return dict(results)


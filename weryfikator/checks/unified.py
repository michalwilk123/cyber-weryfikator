"""
Unified security check module.

This module provides a single entry point for all domain security checks,
minimizing the number of network requests while delegating error detection
to specialized modules.
"""

import aiohttp
from .base import CertificateError, HTTPError, KeyExchangeError
from .domain import verify_domain
from .ssl_errors import _parse_ssl_error
from .key_exchange_errors import _parse_key_exchange_error
from .http_errors import _check_http_redirects


async def check_domain_security(
    session: aiohttp.ClientSession,
    domain: str,
    timeout: int = 10,
    skip_domain_whitelist: bool = False
) -> bool:
    """
    Comprehensive security check for a domain.
    
    This unified function performs all security checks with minimal network requests:
    - Maximum 2 HTTP requests (1 HTTPS + 1 HTTP fallback only if needed)
    - Delegates error detection to specialized modules
    
    Checks performed:
    1. Domain whitelist validation (optional, no network request)
    2. SSL/Certificate validity (expired, hostname mismatch, self-signed, untrusted)
    3. Key exchange security (weak DH parameters, small subgroups, etc.)
    4. HTTP security (HTTPS-to-HTTP redirects, HTTP-only sites)
    
    Args:
        session: aiohttp ClientSession from connection pool
        domain: Plain domain name without protocol (e.g., 'example.com')
        timeout: Request timeout in seconds
        skip_domain_whitelist: If True, skip domain whitelist validation
        
    Returns:
        True if all security checks pass
        
    Raises:
        DomainError: If domain not in whitelist (when skip_domain_whitelist=False)
        CertificateError: If SSL/certificate issue detected
        KeyExchangeError: If weak key exchange parameters detected
        HTTPError: If HTTP security issue detected
        
    Example:
        >>> async with aiohttp.ClientSession() as session:
        ...     result = await check_domain_security(session, 'example.gov.pl')
        ...     # Returns True if secure, raises specific error otherwise
    """
    # Step 1: Verify domain is in whitelist (no network request)
    if not skip_domain_whitelist:
        verify_domain(domain)
    
    https_url = f"https://{domain}"
    http_url = f"http://{domain}"
    
    https_error = None
    
    # Step 2: Try HTTPS connection
    try:
        async with session.get(
            https_url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            allow_redirects=True,
            ssl=True
        ) as response:
            await response.read()
            
            # HTTPS succeeded - check for insecure redirects
            _check_http_redirects(response, https_url)
            
            # All checks passed
            return True
            
    except (aiohttp.ClientConnectorCertificateError, aiohttp.ClientConnectorSSLError, aiohttp.ClientSSLError) as e:
        # SSL/Certificate or key exchange error
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
            # This is a key exchange error - delegate to key exchange parser
            _parse_key_exchange_error(e, domain)
        else:
            # This is a certificate error - delegate to SSL parser
            _parse_ssl_error(e, https_url)
            
    except (CertificateError, KeyExchangeError, HTTPError):
        # Re-raise our custom errors from the parsers or redirect checks
        raise
        
    except Exception as e:
        # Other errors during HTTPS connection
        https_error = e
    
    # Step 3: HTTPS failed, try HTTP to detect HTTP-only sites
    # (This is the only scenario where we need a second request)
    if https_error is not None:
        try:
            async with session.get(
                http_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True
            ) as response:
                await response.read()
                
                # HTTP works but HTTPS failed - this is a security issue
                raise HTTPError(
                    f"Domain {domain} only accepts insecure HTTP connections. "
                    f"HTTPS failed with: {str(https_error)}"
                )
                
        except HTTPError:
            # Re-raise our HTTPError about insecure HTTP-only site
            raise
            
        except Exception as http_error:
            # Both HTTPS and HTTP failed - domain is unreachable
            raise HTTPError(
                f"Domain {domain} is unreachable. "
                f"HTTPS error: {str(https_error)}. HTTP error: {str(http_error)}"
            )
    
    # Should never reach here, but just in case
    return True


"""
Certificate Authority (CA) chain validation.

This module provides async functions to validate that a domain's SSL certificate
chains to the expected root CA used by Polish government domains.
"""

import asyncio
import socket
import select
import time
from typing import Tuple

import OpenSSL.SSL
from .base import CertificateError

# Reference root CA details from gov.pl certificate chain
# Based on: Certum Trusted Network CA
EXPECTED_ROOT_CA_CN = "Certum Trusted Network CA"
EXPECTED_ROOT_CA_ORG = "Unizeto Technologies S.A."


def _get_cert_chain_sync(domain: str, port: int = 443, timeout: int = 10) -> list:
    """
    Synchronously retrieve the SSL certificate chain for a domain.
    
    Args:
        domain: Domain name to check
        port: HTTPS port (default: 443)
        timeout: Connection timeout in seconds
        
    Returns:
        List of X509 certificates in the chain (from leaf to root)
        
    Raises:
        CertificateError: If unable to retrieve certificate chain
    """
    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLS_CLIENT_METHOD)
    context.set_verify(OpenSSL.SSL.VERIFY_PEER, lambda conn, cert, errno, depth, ok: True)
    
    # Load default CA certificates for validation
    context.set_default_verify_paths()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        # Connect to the domain
        sock.connect((domain, port))
        
        # Set to non-blocking to handle OpenSSL's WantRead/WantWrite explicitly
        sock.setblocking(False)
        
        # Wrap with SSL
        connection = OpenSSL.SSL.Connection(context, sock)
        connection.set_tlsext_host_name(domain.encode('utf-8'))
        connection.set_connect_state()
        
        # Handle handshake with timeout
        start_time = time.time()
        while True:
            # Check for total timeout
            if time.time() - start_time > timeout:
                raise socket.timeout("Connection timeout during handshake")
                
            try:
                connection.do_handshake()
                break
            except OpenSSL.SSL.WantReadError:
                # Wait for socket to be readable
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                     raise socket.timeout("Connection timeout during handshake")
                select.select([sock], [], [], remaining)
            except OpenSSL.SSL.WantWriteError:
                # Wait for socket to be writeable
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                     raise socket.timeout("Connection timeout during handshake")
                select.select([], [sock], [], remaining)
        
        # Get the certificate chain
        cert_chain = connection.get_peer_cert_chain()
        
        if not cert_chain:
            raise CertificateError(f"No certificate chain returned for domain {domain}")
        
        return cert_chain
        
    except OpenSSL.SSL.Error as e:
        raise CertificateError(f"SSL error retrieving certificate chain for {domain}: {str(e)}")
    except socket.timeout:
        raise CertificateError(f"Connection timeout while retrieving certificate chain for {domain}")
    except socket.error as e:
        raise CertificateError(f"Socket error retrieving certificate chain for {domain}: {str(e)}")
    except Exception as e:
        raise CertificateError(f"Error retrieving certificate chain for {domain}: {str(e)}")
    finally:
        try:
            connection.shutdown()
        except:
            pass
        sock.close()


def _extract_cert_subject_info(cert) -> Tuple[str, str]:
    """
    Extract CN and O from certificate subject.
    
    Args:
        cert: OpenSSL.crypto.X509 certificate
        
    Returns:
        Tuple of (common_name, organization)
    """
    subject = cert.get_subject()
    cn = subject.CN if hasattr(subject, 'CN') else None
    org = subject.O if hasattr(subject, 'O') else None
    return cn, org


def _extract_cert_issuer_info(cert) -> Tuple[str, str]:
    """
    Extract CN and O from certificate issuer.
    
    Args:
        cert: OpenSSL.crypto.X509 certificate
        
    Returns:
        Tuple of (common_name, organization)
    """
    issuer = cert.get_issuer()
    cn = issuer.CN if hasattr(issuer, 'CN') else None
    org = issuer.O if hasattr(issuer, 'O') else None
    return cn, org


async def check_ca_chain(domain: str, timeout: int = 10) -> bool:
    """
    Check if a domain's SSL certificate chains to the expected root CA.
    
    This function validates that the domain uses a certificate issued by the same
    root CA infrastructure as Polish government domains (Certum Trusted Network CA).
    
    The check works as follows:
    1. Retrieves the complete SSL certificate chain
    2. Iterates through the chain to find the expected root CA.
    3. If the root CA is not in the chain, checks the issuer of the last certificate.
    4. Validates that the root CA matches expected values:
       - CN: Certum Trusted Network CA
       - O: Unizeto Technologies S.A.
    
    Args:
        domain: Plain domain name without protocol (e.g., 'example.gov.pl')
        timeout: Connection timeout in seconds
        
    Returns:
        True if domain uses expected root CA
        
    Raises:
        CertificateError: If domain uses a different root CA or chain cannot be retrieved
    """
    # Run the blocking OpenSSL operations in a thread pool
    cert_chain = await asyncio.to_thread(_get_cert_chain_sync, domain, 443, timeout)
    
    if not cert_chain:
        raise CertificateError(f"Empty certificate chain for domain {domain}")
    
    # Check if any certificate in the chain matches the expected root CA
    for cert in cert_chain:
        cn, org = _extract_cert_subject_info(cert)
        if cn == EXPECTED_ROOT_CA_CN and org == EXPECTED_ROOT_CA_ORG:
            return True
            
    # If not found in the chain, check the issuer of the last certificate
    # (The root CA is often not sent by the server)
    last_cert = cert_chain[-1]
    issuer_cn, issuer_org = _extract_cert_issuer_info(last_cert)
    
    if issuer_cn == EXPECTED_ROOT_CA_CN and issuer_org == EXPECTED_ROOT_CA_ORG:
        return True
        
    # Failed to find expected root CA
    # We report the issuer of the last cert as the found root for error message
    raise CertificateError(
        f"Domain {domain} uses different root CA. "
        f"Expected CN='{EXPECTED_ROOT_CA_CN}', got CN='{issuer_cn}'"
    )


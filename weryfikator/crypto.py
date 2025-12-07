"""
Token generation and verification using HMAC-SHA256.

Security Features:
- 128-bit cryptographically secure random salt (per-token randomness)
- Hardcoded pepper (secret constant, never transmitted)
- HMAC-SHA256 signature (cannot forge without master secret + pepper)
- Domain binding (domain is embedded in signature)
- Time-to-live (TTL) expiration
- UTC timestamps (timezone-independent)
- Constant-time signature comparison (timing attack resistant)
"""

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import re
import secrets


class Verifier:
    """
    Central authority that generates and validates one-time tokens.

    The Verifier holds the master secret and is the ONLY entity that can
    generate valid tokens or verify their authenticity.
    """

    # Hardcoded pepper - stored only in Verifier, NEVER transmitted
    PEPPER = b'hardcoded_pepper_value_never_leave_server_af8d92b1c3e4f567'

    def __init__(self, master_secret: str):
        self.master_secret = master_secret.encode('utf-8')

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        # Strip http:// or https:// prefix (case insensitive)
        normalized = re.sub(r'^https?://', '', domain, flags=re.IGNORECASE)
        return normalized

    def generate_token(self, domain: str, ttl_seconds: int = 30) -> str:
        """
        Generate a token with domain binding, time-to-live, salt, and pepper.

        Token structure: base64(domain:timestamp:ttl:salt:signature)
        where signature = HMAC-SHA256(secret||pepper, domain||timestamp||ttl||salt)

        Security layers:
        - Domain: Normalized domain (stripped of protocol) bound to token
        - Salt: Per-token random value (transmitted with token)
        - Pepper: Secret constant (never transmitted, known only to Verifier)
        - UTC Timestamp: Timezone-independent time
        """
        # Normalize domain (strip protocol prefix)
        normalized_domain = self._normalize_domain(domain)

        # Generate cryptographically secure random salt (16 bytes = 128 bits)
        salt = secrets.token_bytes(16)
        salt_hex = salt.hex()

        # Get current UTC timestamp
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        ttl = str(ttl_seconds)

        # Create the message to sign: domain||timestamp||ttl||salt
        message = f'{normalized_domain}:{timestamp}:{ttl}:{salt_hex}'.encode('utf-8')

        # Combine master secret with pepper for signing key
        signing_key = self.master_secret + self.PEPPER

        # Generate HMAC-SHA256 signature using secret+pepper
        signature = hmac.new(signing_key, message, hashlib.sha256).hexdigest()

        # Construct token: domain:timestamp:ttl:salt:signature
        token_data = f'{normalized_domain}:{timestamp}:{ttl}:{salt_hex}:{signature}'

        # Base64 encode the entire token
        token = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')

        return token

    def verify_token(self, token: str) -> tuple[bool, str, str]:
        """
        Verify a token's authenticity and expiration.
        Validates signature using master secret + pepper.
        """
        try:
            token_data = base64.b64decode(token.encode('utf-8')).decode('utf-8')
            parts = token_data.split(':')

            if len(parts) != 5:
                return False, 'Invalid token format', ''

            token_domain, timestamp_str, ttl_str, salt_hex, provided_signature = parts

            # Validate timestamp and TTL are integers
            try:
                timestamp = int(timestamp_str)
                ttl = int(ttl_str)
            except ValueError:
                return False, 'Invalid timestamp or TTL', ''

            current_time = int(datetime.now(timezone.utc).timestamp())
            if current_time > timestamp + ttl:
                age = current_time - timestamp
                return False, f'Token expired (TTL: {ttl}s, age: {age}s)', token_domain

            message = f'{token_domain}:{timestamp_str}:{ttl_str}:{salt_hex}'.encode('utf-8')
            signing_key = self.master_secret + self.PEPPER

            expected_signature = hmac.new(signing_key, message, hashlib.sha256).hexdigest()

            # Use constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(expected_signature, provided_signature):
                return False, 'Invalid signature (token may be forged or tampered)', ''

            return True, 'Token verified successfully', token_domain

        except Exception as e:
            return False, f'Token verification error: {str(e)}', ''

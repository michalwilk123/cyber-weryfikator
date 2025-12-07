from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class WeryfikatorConnector:
    """
    HTTP client for weryfikator service with connection pooling and retry logic.

    Features:
    - Connection pooling (reuses connections)
    - Automatic retries with exponential backoff
    - Configurable timeouts
    - Thread-safe singleton pattern
    """

    def __init__(self, base_url: str, timeout: float = 10.0):
        """Initialize the connector with connection pool."""
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Create async client with connection pooling
        # limits: max 100 connections, max 20 per host
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20, max_connections=100, keepalive_expiry=30.0
            ),
        )

    async def close(self):
        """Close the HTTP client and release connections."""
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify a token with the weryfikator service.

        Automatically retries on timeout or connection errors with exponential backoff:
        - Attempt 1: immediate
        - Attempt 2: after 1 second
        - Attempt 3: after 2 seconds
        """
        try:
            response = await self._client.post('/verify-token', json={'token': token})
            
            response.raise_for_status()
            result = response.json()
            return result
            
        except httpx.HTTPStatusError as e:
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            raise


_connector_instance: WeryfikatorConnector | None = None


async def get_connector(base_url: str) -> WeryfikatorConnector:
    """
    Get or create the singleton WeryfikatorConnector instance.

    This ensures we only have one connection pool for the entire application.
    """
    global _connector_instance

    if _connector_instance is None:
        _connector_instance = WeryfikatorConnector(base_url=base_url)

    return _connector_instance


async def close_connector():
    """Close the global connector instance."""
    global _connector_instance

    if _connector_instance is not None:
        await _connector_instance.close()
        _connector_instance = None

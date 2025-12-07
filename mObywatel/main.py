from functools import lru_cache
from contextlib import asynccontextmanager

from connector import close_connector, get_connector
from fastapi import Depends, FastAPI, Header, HTTPException
import httpx
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    weryfikator_url: str = Field(
        default='http://weryfikator-service:8888', description='URL of the weryfikator service'
    )

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore'
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# WARNING: This is a simulated database for testing purposes only.
# In production, NEVER store user data in a hardcoded dictionary.
# Always use a proper database with encryption, access controls, and security measures.
USERS_DB = {
    'user001': {'name': 'Jan Kowalski', 'pesel': '90010112345'},
    'user002': {'name': 'Anna Nowak', 'pesel': '85050567890'},
}


async def get_current_user(x_user_id: str = Header(...)):
    """Authentication dependency that verifies user exists in the database."""
    if x_user_id not in USERS_DB:
        raise HTTPException(status_code=403, detail='Forbidden')
    return USERS_DB[x_user_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application (startup and shutdown)."""
    # Startup logic
    settings = get_settings()
    await get_connector(settings.weryfikator_url)
    
    yield
    
    # Shutdown logic
    await close_connector()


app = FastAPI(
    title='mObywatel Service',
    description='Mobile application backend service',
    version='1.0.0',
    lifespan=lifespan,
)


@app.get('/')
async def root():
    """Root endpoint with service information"""
    return {
        'service': 'mObywatel',
        'status': 'running',
        'version': '1.0.0',
        'description': 'Mobile application backend service',
    }


class VerifyTokenRequest(BaseModel):
    """Request model for token verification."""

    token: str = Field(..., description='Base64-encoded token to verify')


class VerifyTokenResponse(BaseModel):
    """Response model for token verification."""

    valid: bool = Field(..., description='Whether the token is valid')
    message: str = Field(..., description='Verification result message')
    domain: str = Field(..., description='Domain embedded in the token')


@app.post('/verify-token', response_model=VerifyTokenResponse)
async def verify_token(
    request: VerifyTokenRequest,
    _user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """
    Verify a token by forwarding to the weryfikator service.

    Requires authentication via X-User-ID header.
    Uses connection pooling and automatic retries for reliability.
    """
    try:
        connector = await get_connector(settings.weryfikator_url)
        result = await connector.verify_token(request.token)
        return VerifyTokenResponse(**result)

    except httpx.HTTPStatusError as e:
        # Weryfikator returned 4xx/5xx status
        if e.response.status_code == 401:
            detail = e.response.json().get('detail', 'Token verification failed')
        else:
            detail = f'Verification service error: {e.response.status_code}'

        raise HTTPException(status_code=e.response.status_code, detail=detail)

    except (httpx.TimeoutException, httpx.ConnectError) as e:
        # Connection/timeout errors after retries
        raise HTTPException(
            status_code=503, detail=f'Unable to reach verification service: {str(e)}'
        )

    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f'Internal error: {str(e)}')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=9090)

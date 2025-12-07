from functools import lru_cache

import aiohttp
from crypto import Verifier
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from checks.base import BaseCheckError, CertificateError, DomainError, HTTPError, KeyExchangeError
from checks.ca_chain import check_ca_chain
from checks.domain import verify_domain
from checks.unified import check_domain_security


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    master_secret: str = Field(..., description='Master secret for HMAC signing')
    default_ttl_seconds: int = Field(
        ..., description='Default time-to-live for tokens in seconds', ge=1
    )
    enable_domain_checks: bool = Field(
        default=False, description='Enable domain security checks before token generation'
    )

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore'
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_verifier(settings: Settings = Depends(get_settings)) -> Verifier:
    """Get Verifier instance with configured master secret."""
    return Verifier(master_secret=settings.master_secret)


class GenerateTokenRequest(BaseModel):
    """Request model for token generation."""

    domain: str = Field(..., description='Domain requesting the token')
    ttl_seconds: int | None = Field(
        default=None, description='Time-to-live in seconds (uses default if not specified)', ge=1
    )


class GenerateTokenResponse(BaseModel):
    """Response model for token generation."""

    token: str = Field(..., description='Base64-encoded token')


class VerifyTokenRequest(BaseModel):
    """Request model for token verification."""

    token: str = Field(..., description='Base64-encoded token to verify')


class VerifyTokenResponse(BaseModel):
    """Response model for token verification."""

    valid: bool = Field(..., description='Whether the token is valid')
    message: str = Field(..., description='Verification result message')
    domain: str = Field(..., description='Domain embedded in the token')


app = FastAPI(
    title='Weryfikator Service',
    description='Internal verification service for creating and verifying secrets',
    version='1.0.0',
)


@app.get('/')
async def root():
    """Health check endpoint"""
    return {
        'service': 'weryfikator',
        'status': 'running',
        'version': '1.0.0',
        'description': 'Internal verification service',
    }


@app.post(
    '/generate-token', response_model=GenerateTokenResponse, status_code=status.HTTP_201_CREATED
)
async def generate_token(
    request: GenerateTokenRequest,
    verifier: Verifier = Depends(get_verifier),
    settings: Settings = Depends(get_settings),
):
    """
    Generate a cryptographically secure token with HMAC-SHA256 signature.

    The token includes:
    - Domain (normalized, without protocol prefix)
    - Timestamp (UTC)
    - Time-to-live (TTL)
    - Random salt (128-bit)
    - HMAC-SHA256 signature (using master secret + pepper)
    
    When ENABLE_DOMAIN_CHECKS is set, performs security checks:
    - Domain whitelist validation
    - SSL/Certificate validity
    - Key exchange security
    - HTTP security (HTTPS-to-HTTP redirects, HTTP-only sites)
    - CA chain validation (verifies root CA matches gov.pl)
    """
    # Perform domain security checks if enabled
    if settings.enable_domain_checks:
        try:
            async with aiohttp.ClientSession() as session:
                await check_domain_security(
                    session=session,
                    domain=request.domain,
                    timeout=10,
                    skip_domain_whitelist=False
                )
            
            # Additional checks: Domain whitelist and CA chain validation
            verify_domain(request.domain)
            await check_ca_chain(request.domain, timeout=10)
            
        except DomainError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Domain not allowed: {e.message}"
            )
        except CertificateError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSL/Certificate error: {e.message}"
            )
        except KeyExchangeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Key exchange error: {e.message}"
            )
        except HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"HTTP security error: {e.message}"
            )
        except BaseCheckError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Security check failed: {e.message}"
            )
    
    ttl = request.ttl_seconds if request.ttl_seconds is not None else settings.default_ttl_seconds
    token = verifier.generate_token(domain=request.domain, ttl_seconds=ttl)

    return GenerateTokenResponse(token=token)


@app.post('/verify-token', response_model=VerifyTokenResponse)
async def verify_token(request: VerifyTokenRequest, verifier: Verifier = Depends(get_verifier)):
    """
    Verify a token's authenticity and expiration.

    Validates:
    - HMAC-SHA256 signature (using master secret + pepper)
    - Token has not expired (based on TTL)
    - Token format is valid

    Returns the domain embedded in the token.
    """
    is_valid, message, domain = verifier.verify_token(request.token)

    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)

    return VerifyTokenResponse(valid=is_valid, message=message, domain=domain)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8888)

import asyncio
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from connector import close_connector, get_connector
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import uvicorn


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    weryfikator_url: str = Field(
        default='http://weryfikator-service:8888', description='URL of the weryfikator service'
    )
    domain: str = Field(
        default='bank.example.com', description='Domain to embed in tokens'
    )

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore'
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


async def update_secret_file(file_path: Path):
    """
    Background task that generates tokens from weryfikator service and updates the secret file.
    """
    settings = get_settings()
    
    while True:
        try:
            connector = await get_connector(settings.weryfikator_url)
            token = await connector.generate_token(domain=settings.domain)

            with open(file_path, 'w') as f:
                f.write(token)

            print(f'Updated token: {token[:50]}...')  # Show first 50 chars only

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f'Connection error: {e}. Will retry in 10 seconds...')
        except httpx.HTTPStatusError as e:
            print(f'HTTP error {e.response.status_code}: {e}. Will retry in 10 seconds...')
        except Exception as e:
            print(f'Unexpected error: {e}. Will retry in 10 seconds...')

        await asyncio.sleep(10)


# Background task for token generation
token_generator_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connector and start the token generator background task
    global token_generator_task
    settings = get_settings()
    await get_connector(settings.weryfikator_url)
    
    secret_file = Path('/app/secret.txt')
    print('Starting token generator, updating every 10 seconds...')
    token_generator_task = asyncio.create_task(update_secret_file(secret_file))

    yield

    # Shutdown: Cancel the background task and close connector
    if token_generator_task:
        token_generator_task.cancel()
        try:
            await token_generator_task
        except asyncio.CancelledError:
            print('Token generator stopped')
    
    await close_connector()


app = FastAPI(
    title='Bank Service',
    description='Bank website with QR verification',
    version='1.0.0',
    lifespan=lifespan,
)

# Mount static files
app.mount('/static', StaticFiles(directory='/app'), name='static')


@app.get('/')
async def read_index():
    """Serve the main bank.html page"""
    return FileResponse('/app/bank.html')


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)

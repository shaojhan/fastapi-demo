from contextlib import asynccontextmanager
from typing import AsyncIterator

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.repositories.BaseRepository import db

@pytest.fixture(scope='session')
def client():
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator:
        async with db: yield
    fastapi_app = FastAPI(
        lifespan=lifespan,
        root_path='/api',
    )
    
    @fastapi_app.get('/', include_in_schema=False)
    def hello(request: Request) -> dict:
        return {
            "message": "Hello World",
            "root_path": request.scope.get("root_path")
        }
    
    client = TestClient(app=fastapi_app)
    return client
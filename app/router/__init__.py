from fastapi import APIRouter

from app.router import (
    UserRouter
)

router = APIRouter()
router.include_router(router=UserRouter.router)
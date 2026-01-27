from fastapi import APIRouter

from app.router import (
    UserRouter,
    SessionRouter,
    TasksRouter,
    EmployeeRouter,
)

router = APIRouter()
router.include_router(router=UserRouter.router)
router.include_router(router=SessionRouter.router)
router.include_router(router=TasksRouter.router)
router.include_router(router=EmployeeRouter.router)

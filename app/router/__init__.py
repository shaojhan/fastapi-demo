from fastapi import APIRouter

from app.router import (
    UserRouter,
    SessionRouter,
    TasksRouter,
    EmployeeRouter,
    OAuthRouter,
    MessageRouter,
    ScheduleRouter,
    SSORouter,
    MQTTRouter,
)

router = APIRouter()
router.include_router(router=UserRouter.router)
router.include_router(router=SessionRouter.router)
router.include_router(router=TasksRouter.router)
router.include_router(router=EmployeeRouter.router)
router.include_router(router=OAuthRouter.router)
router.include_router(router=MessageRouter.router)
router.include_router(router=ScheduleRouter.router)
router.include_router(router=SSORouter.router)
router.include_router(router=MQTTRouter.router)

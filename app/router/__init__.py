from fastapi import APIRouter

from app.router import (
    ApprovalRouter,
    ChatRouter,
    EmployeeRouter,
    HRChatRouter,
    KafkaRouter,
    MessageRouter,
    MQTTRouter,
    OAuthRouter,
    ScheduleRouter,
    SessionRouter,
    SSORouter,
    TasksRouter,
    UserRouter,
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
router.include_router(router=KafkaRouter.router)
router.include_router(router=ChatRouter.router)
router.include_router(router=ApprovalRouter.router)
router.include_router(router=HRChatRouter.router)

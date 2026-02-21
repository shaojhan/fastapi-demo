"""
Unit tests for ScheduleRouter endpoints.

測試策略:
- TestClient + dependency_overrides
- 驗證 employee-only 授權
- 驗證 CRUD 端點
"""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.router.ScheduleRouter import router
from app.router.dependencies.auth import get_current_user
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.exceptions.BaseException import BaseException as AppBaseException


def _create_app():
    app = FastAPI()

    @app.exception_handler(AppBaseException)
    async def handler(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(router)
    return app


def _make_employee():
    return UserModel.reconstitute(
        id="22222222-2222-2222-2222-222222222222", uid="employee", email="emp@example.com",
        hashed_password="hashed", profile=DomainProfile(name="Employee"),
        role=UserRole.EMPLOYEE, email_verified=True,
    )


def _make_mock_schedule():
    mock = MagicMock()
    mock.id = "55555555-5555-5555-5555-555555555555"
    mock.title = "Meeting"
    mock.description = "Team meeting"
    mock.location = "Room A"
    mock.start_time = datetime(2024, 12, 1, 9, 0, tzinfo=timezone.utc)
    mock.end_time = datetime(2024, 12, 1, 10, 0, tzinfo=timezone.utc)
    mock.all_day = False
    mock.timezone = "Asia/Taipei"
    mock.creator = MagicMock()
    mock.creator.user_id = "22222222-2222-2222-2222-222222222222"
    mock.creator.username = "employee"
    mock.creator.email = "emp@example.com"
    mock.google_event_id = None
    mock.synced_at = None
    mock.google_sync = MagicMock()
    mock.google_sync.is_synced = False
    mock.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mock.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return mock


class TestCreateSchedule:
    """測試 POST /schedules/ 端點"""

    def test_create_schedule_as_employee(self):
        from app.router.ScheduleRouter import get_schedule_service
        app = _create_app()
        employee = _make_employee()
        mock_service = MagicMock()
        mock_service.create_schedule.return_value = _make_mock_schedule()

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_schedule_service] = lambda: mock_service
        client = TestClient(app)

        response = client.post("/schedules/", json={
            "title": "Meeting",
            "description": "Team meeting",
            "location": "Room A",
            "start_time": "2024-12-01T09:00:00Z",
            "end_time": "2024-12-01T10:00:00Z",
            "all_day": False,
            "timezone": "Asia/Taipei",
        })
        assert response.status_code == 200
        mock_service.create_schedule.assert_called_once()

    def test_create_schedule_unauthenticated(self):
        app = _create_app()
        client = TestClient(app)
        response = client.post("/schedules/", json={
            "title": "Meeting", "start_time": "2024-12-01T09:00:00Z",
            "end_time": "2024-12-01T10:00:00Z",
        })
        assert response.status_code == 401


class TestListSchedules:
    """測試 GET /schedules/ 端點"""

    def test_list_schedules(self):
        from app.router.ScheduleRouter import get_schedule_service
        app = _create_app()
        employee = _make_employee()
        mock_service = MagicMock()
        mock_service.list_schedules.return_value = ([], 0)

        app.dependency_overrides[get_current_user] = lambda: employee
        app.dependency_overrides[get_schedule_service] = lambda: mock_service
        client = TestClient(app)

        response = client.get("/schedules/?page=1&size=10")
        assert response.status_code == 200

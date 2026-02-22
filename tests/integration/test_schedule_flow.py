"""
Integration tests: Schedule management flow.

Tests the full HTTP → Router → Service → Repository → SQLite stack for:
- Schedule CRUD (create, list, get, update, delete)
- Access control (employee only, owner-only update/delete)
- Google Calendar admin endpoints (status, disconnect, connect)
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from tests.integration.conftest import get_auth_token, auth_headers, _seed_user
from app.domain.UserModel import UserRole


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _schedule_payload(
    title: str = "Team Meeting",
    start_offset_hours: int = 1,
    end_offset_hours: int = 2,
    sync_to_google: bool = False,
) -> dict:
    base = datetime(2025, 6, 1, 9, 0, 0)
    return {
        "title": title,
        "description": "Test description",
        "location": "Room A",
        "start_time": (base + timedelta(hours=start_offset_hours)).isoformat(),
        "end_time": (base + timedelta(hours=end_offset_hours)).isoformat(),
        "all_day": False,
        "timezone": "Asia/Taipei",
        "sync_to_google": sync_to_google,
    }


@pytest.fixture
def seed_employee(db_session):
    """建立 EMPLOYEE 角色測試帳號。"""
    return _seed_user(
        db_session,
        uid="employee1",
        email="employee1@test.com",
        password="Employee123!",
        role=UserRole.EMPLOYEE,
        name="Employee One",
    )


@pytest.fixture
def seed_employee2(db_session):
    """建立第二個 EMPLOYEE 角色測試帳號（用於測試非擁有者操作）。"""
    return _seed_user(
        db_session,
        uid="employee2",
        email="employee2@test.com",
        password="Employee123!",
        role=UserRole.EMPLOYEE,
        name="Employee Two",
    )


# ---------------------------------------------------------------------------
# POST /schedules/ — create schedule
# ---------------------------------------------------------------------------

class TestCreateSchedule:
    """測試建立排程。"""

    def test_employee_can_create_schedule(self, client, seed_employee):
        """員工可以成功建立排程。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        resp = client.post(
            "/schedules/",
            json=_schedule_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Team Meeting"
        assert body["location"] == "Room A"
        assert "id" in body

    def test_admin_can_create_schedule(self, client, seed_admin):
        """管理員也可以建立排程（ADMIN role 包含 EMPLOYEE 權限）。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.post(
            "/schedules/",
            json=_schedule_payload("Admin Schedule"),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Admin Schedule"

    def test_normal_user_cannot_create_schedule(self, client, seed_normal_user):
        """一般使用者無法建立排程，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.post(
            "/schedules/",
            json=_schedule_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_schedule(self, client):
        """未認證使用者無法建立排程，回傳 401。"""
        resp = client.post("/schedules/", json=_schedule_payload())
        assert resp.status_code == 401

    def test_create_schedule_missing_title_returns_422(self, client, seed_employee):
        """缺少必填欄位 title，回傳 422。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        payload = _schedule_payload()
        del payload["title"]
        resp = client.post("/schedules/", json=payload, headers=auth_headers(token))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /schedules/ — list schedules
# ---------------------------------------------------------------------------

class TestListSchedules:
    """測試排程列表端點。"""

    def test_employee_can_list_empty_schedules(self, client, seed_employee):
        """空資料庫時，列表為空。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        resp = client.get("/schedules/?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert body["page"] == 1

    def test_list_reflects_created_schedule(self, client, seed_employee):
        """建立後，排程出現在列表中。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        client.post("/schedules/", json=_schedule_payload("Listed Meeting"), headers=auth_headers(token))

        resp = client.get("/schedules/?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Listed Meeting"

    def test_normal_user_cannot_list_schedules(self, client, seed_normal_user):
        """一般使用者無法查看排程列表，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/schedules/?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_schedules(self, client):
        """未認證使用者無法查看排程，回傳 401。"""
        resp = client.get("/schedules/?page=1&size=10")
        assert resp.status_code == 401

    def test_list_pagination(self, client, seed_employee):
        """分頁參數正常運作。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        # 建立 3 個排程
        for i in range(3):
            client.post(
                "/schedules/",
                json=_schedule_payload(f"Meeting {i}", start_offset_hours=i + 1, end_offset_hours=i + 2),
                headers=auth_headers(token),
            )

        resp = client.get("/schedules/?page=1&size=2", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2


# ---------------------------------------------------------------------------
# GET /schedules/{id} — get schedule detail
# ---------------------------------------------------------------------------

class TestGetSchedule:
    """測試取得單一排程。"""

    def test_employee_can_get_own_schedule(self, client, seed_employee):
        """員工可以取得排程詳情。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        resp = client.get(f"/schedules/{schedule_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == schedule_id
        assert resp.json()["title"] == "Team Meeting"

    def test_get_nonexistent_schedule_returns_404(self, client, seed_employee):
        """取得不存在的排程，回傳 404。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.get(f"/schedules/{fake_id}", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_normal_user_cannot_get_schedule(self, client, seed_employee, seed_normal_user):
        """一般使用者無法取得排程，回傳 403。"""
        emp_token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(emp_token))
        schedule_id = create_resp.json()["id"]

        normal_token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get(f"/schedules/{schedule_id}", headers=auth_headers(normal_token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_get_schedule(self, client, seed_employee):
        """未認證使用者無法取得排程，回傳 401。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        resp = client.get(f"/schedules/{schedule_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /schedules/{id} — update schedule
# ---------------------------------------------------------------------------

class TestUpdateSchedule:
    """測試更新排程（只有建立者可以更新）。"""

    def test_creator_can_update_schedule(self, client, seed_employee):
        """建立者可以更新自己的排程。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        update_payload = {"title": "Updated Meeting", "sync_to_google": False}
        resp = client.put(f"/schedules/{schedule_id}", json=update_payload, headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Meeting"

    def test_non_creator_cannot_update_schedule(self, client, seed_employee, seed_employee2):
        """非建立者嘗試更新排程，回傳 403。"""
        creator_token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(creator_token))
        schedule_id = create_resp.json()["id"]

        other_token = get_auth_token(client, seed_employee2["uid"], seed_employee2["password"])
        update_payload = {"title": "Hacked Meeting", "sync_to_google": False}
        resp = client.put(f"/schedules/{schedule_id}", json=update_payload, headers=auth_headers(other_token))
        assert resp.status_code == 403

    def test_update_nonexistent_schedule_returns_404(self, client, seed_employee):
        """更新不存在的排程，回傳 404。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.put(f"/schedules/{fake_id}", json={"sync_to_google": False}, headers=auth_headers(token))
        assert resp.status_code == 404

    def test_unauthenticated_cannot_update_schedule(self, client, seed_employee):
        """未認證使用者無法更新排程，回傳 401。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        resp = client.put(f"/schedules/{schedule_id}", json={"title": "Hack", "sync_to_google": False})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /schedules/{id} — delete schedule
# ---------------------------------------------------------------------------

class TestDeleteSchedule:
    """測試刪除排程（只有建立者可以刪除）。"""

    def test_creator_can_delete_schedule(self, client, seed_employee):
        """建立者可以刪除自己的排程。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        resp = client.delete(f"/schedules/{schedule_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["message"] == "Schedule deleted."

        # Confirm deletion
        get_resp = client.get(f"/schedules/{schedule_id}", headers=auth_headers(token))
        assert get_resp.status_code == 404

    def test_non_creator_cannot_delete_schedule(self, client, seed_employee, seed_employee2):
        """非建立者嘗試刪除排程，回傳 403。"""
        creator_token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(creator_token))
        schedule_id = create_resp.json()["id"]

        other_token = get_auth_token(client, seed_employee2["uid"], seed_employee2["password"])
        resp = client.delete(f"/schedules/{schedule_id}", headers=auth_headers(other_token))
        assert resp.status_code == 403

    def test_delete_nonexistent_schedule_returns_404(self, client, seed_employee):
        """刪除不存在的排程，回傳 404。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.delete(f"/schedules/{fake_id}", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_unauthenticated_cannot_delete_schedule(self, client, seed_employee):
        """未認證使用者無法刪除排程，回傳 401。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        create_resp = client.post("/schedules/", json=_schedule_payload(), headers=auth_headers(token))
        schedule_id = create_resp.json()["id"]

        resp = client.delete(f"/schedules/{schedule_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /schedules/google/status — Google Calendar status (admin only)
# ---------------------------------------------------------------------------

class TestGoogleCalendarStatus:
    """測試 Google Calendar 連線狀態端點（僅 Admin）。"""

    def test_admin_can_get_google_status(self, client, seed_admin):
        """管理員可以查詢 Google Calendar 連線狀態。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/schedules/google/status", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "connected" in body

    def test_employee_cannot_get_google_status(self, client, seed_employee):
        """一般員工無法查詢 Google Calendar 狀態，回傳 403。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        resp = client.get("/schedules/google/status", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_get_google_status(self, client):
        """未認證使用者無法查詢，回傳 401。"""
        resp = client.get("/schedules/google/status")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /schedules/google/disconnect — Disconnect Google Calendar
# ---------------------------------------------------------------------------

class TestGoogleCalendarDisconnect:
    """測試斷開 Google Calendar 連線（僅 Admin）。"""

    def test_admin_can_disconnect_google(self, client, seed_admin):
        """管理員可以斷開 Google Calendar 連線。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.delete("/schedules/google/disconnect", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["message"] == "Google Calendar disconnected."

    def test_employee_cannot_disconnect_google(self, client, seed_employee):
        """一般員工無法斷開，回傳 403。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        resp = client.delete("/schedules/google/disconnect", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_disconnect_google(self, client):
        """未認證使用者無法斷開，回傳 401。"""
        resp = client.delete("/schedules/google/disconnect")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /schedules/google/connect — Connect Google Calendar
# ---------------------------------------------------------------------------

class TestGoogleCalendarConnect:
    """測試連線 Google Calendar（僅 Admin）。"""

    def _connect_payload(self) -> dict:
        return {
            "calendar_id": "primary",
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "expires_at": "2099-01-01T00:00:00",
        }

    def test_admin_can_connect_google(self, client, seed_admin):
        """管理員可以連線 Google Calendar（直接提供 tokens）。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.post(
            "/schedules/google/connect",
            json=self._connect_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["calendar_id"] == "primary"

    def test_employee_cannot_connect_google(self, client, seed_employee):
        """一般員工無法連線 Google Calendar，回傳 403。"""
        token = get_auth_token(client, seed_employee["uid"], seed_employee["password"])
        resp = client.post(
            "/schedules/google/connect",
            json=self._connect_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_connect_google(self, client):
        """未認證使用者無法連線，回傳 401。"""
        resp = client.post("/schedules/google/connect", json=self._connect_payload())
        assert resp.status_code == 401

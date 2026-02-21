"""
Integration tests: 簽核申請流程。

測試整個 HTTP → Router → Service → Repository → SQLite 堆疊：
- 員工提交請假、費用申請
- 申請人查詢自身申請列表
- 非員工使用者無法提交申請
- 簽核鏈建立（至少包含 Admin 作為最終核准人）
"""
import pytest
from datetime import datetime, timezone

from tests.integration.conftest import get_auth_token, auth_headers, _seed_user
from app.domain.UserModel import UserRole


# ---------------------------------------------------------------------------
# Fixtures: 準備員工場景
# ---------------------------------------------------------------------------

@pytest.fixture
def employee_scenario(client, seed_admin, seed_normal_user):
    """
    完整的員工場景 fixture：
    1. Admin 將一般使用者指派為員工
    2. 回傳 admin/employee 的帳號資訊
    """
    admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

    # 指派員工
    resp = client.post(
        "/employees/assign",
        json={
            "user_id": seed_normal_user["id"],
            "idno": "EMP001",
            "department": "IT",
            "role_id": 0,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, f"Failed to assign employee: {resp.text}"

    return {
        "admin": seed_admin,
        "employee": seed_normal_user,
        "admin_token": admin_token,
    }


# ---------------------------------------------------------------------------
# POST /approvals/leave
# ---------------------------------------------------------------------------

_LEAVE_PAYLOAD = {
    "leave_type": "ANNUAL",
    "start_date": "2026-03-10T09:00:00",
    "end_date": "2026-03-12T18:00:00",
    "reason": "年假申請",
}

_EXPENSE_PAYLOAD = {
    "amount": 1500.0,
    "category": "交通費",
    "description": "出差計程車費",
    "receipt_url": None,
}


class TestCreateLeaveRequest:
    """測試請假申請建立（需有 Employee 身份）。"""

    def test_employee_can_create_leave_request(self, client, employee_scenario):
        """員工成功建立請假申請，並自動生成簽核鏈。"""
        emp = employee_scenario["employee"]
        token = get_auth_token(client, emp["uid"], emp["password"])

        resp = client.post(
            "/approvals/leave",
            json=_LEAVE_PAYLOAD,
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "LEAVE"
        assert body["status"] == "PENDING"
        assert body["requester_id"] == emp["id"]
        # 簽核鏈至少包含 Admin 作為最終核准人
        assert len(body["steps"]) >= 1

    def test_normal_user_cannot_create_leave_request(self, client, seed_normal_user):
        """非員工身份無法提交請假申請，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])

        resp = client.post(
            "/approvals/leave",
            json=_LEAVE_PAYLOAD,
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_leave_request(self, client):
        """未認證使用者，回傳 401。"""
        resp = client.post("/approvals/leave", json=_LEAVE_PAYLOAD)
        assert resp.status_code == 401

    def test_leave_request_requires_valid_payload(self, client, employee_scenario):
        """缺少必填欄位，回傳 422。"""
        emp = employee_scenario["employee"]
        token = get_auth_token(client, emp["uid"], emp["password"])

        resp = client.post(
            "/approvals/leave",
            json={"leave_type": "ANNUAL"},  # 缺少 start_date/end_date/reason
            headers=auth_headers(token),
        )
        assert resp.status_code == 422


class TestCreateExpenseRequest:
    """測試費用申請建立（需有 Employee 身份）。"""

    def test_employee_can_create_expense_request(self, client, employee_scenario):
        """員工成功建立費用申請。"""
        emp = employee_scenario["employee"]
        token = get_auth_token(client, emp["uid"], emp["password"])

        resp = client.post(
            "/approvals/expense",
            json=_EXPENSE_PAYLOAD,
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "EXPENSE"
        assert body["status"] == "PENDING"
        assert body["requester_id"] == emp["id"]

    def test_normal_user_cannot_create_expense_request(self, client, seed_normal_user):
        """非員工身份無法提交費用申請，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.post(
            "/approvals/expense",
            json=_EXPENSE_PAYLOAD,
            headers=auth_headers(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /approvals/my-requests
# ---------------------------------------------------------------------------

class TestMyApprovalRequests:
    """測試查詢自身申請列表。"""

    def test_employee_can_list_own_requests(self, client, employee_scenario):
        """員工可查詢自身的申請列表。"""
        emp = employee_scenario["employee"]
        token = get_auth_token(client, emp["uid"], emp["password"])

        # 提交兩筆申請
        client.post("/approvals/leave", json=_LEAVE_PAYLOAD, headers=auth_headers(token))
        client.post("/approvals/expense", json=_EXPENSE_PAYLOAD, headers=auth_headers(token))

        resp = client.get("/approvals/my-requests?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        types = {item["type"] for item in body["items"]}
        assert "LEAVE" in types
        assert "EXPENSE" in types

    def test_my_requests_initially_empty(self, client, employee_scenario):
        """未提交任何申請時，列表為空。"""
        emp = employee_scenario["employee"]
        token = get_auth_token(client, emp["uid"], emp["password"])

        resp = client.get("/approvals/my-requests?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_normal_user_cannot_list_requests(self, client, seed_normal_user):
        """非員工身份無法查看申請列表，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/approvals/my-requests", headers=auth_headers(token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /approvals/pending
# ---------------------------------------------------------------------------

class TestPendingApprovals:
    """測試查詢待我核准的申請。"""

    def test_admin_sees_pending_approvals_after_leave_request(self, client, employee_scenario):
        """員工提交請假後，Admin 的待核准列表中應出現該申請。"""
        emp = employee_scenario["employee"]
        admin_token = employee_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # 員工提交請假
        client.post("/approvals/leave", json=_LEAVE_PAYLOAD, headers=auth_headers(emp_token))

        # Admin 查詢待核准列表（Admin 為最終核准人）
        resp = client.get("/approvals/pending?page=1&size=10", headers=auth_headers(admin_token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["items"][0]["type"] == "LEAVE"
        assert body["items"][0]["status"] == "PENDING"

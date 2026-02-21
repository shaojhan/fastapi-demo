"""
Integration tests: 員工指派與管理流程。

測試整個 HTTP → Router → Service → Repository → SQLite 堆疊：
- 管理員指派使用者為員工（跨聚合操作：同時建立 Employee 並更新 User 角色）
- 員工列表分頁查詢
- 角色存取控制（僅 Admin 可操作）
"""
import pytest

from tests.integration.conftest import get_auth_token, auth_headers, _seed_user
from app.domain.UserModel import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assign_employee_payload(user_id: str, idno: str = "EMP001", department: str = "IT") -> dict:
    return {
        "user_id": user_id,
        "idno": idno,
        "department": department,
        "role_id": 0,  # 0 表示不指派角色（EmployeeService 會忽略不存在的 role_id=0）
    }


# ---------------------------------------------------------------------------
# POST /employees/assign
# ---------------------------------------------------------------------------

class TestAssignEmployee:
    """測試指派使用者為員工（Admin only）。"""

    def test_admin_can_assign_user_as_employee(self, client, seed_admin, seed_normal_user):
        """Admin 成功將一般使用者指派為員工。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        payload = _assign_employee_payload(seed_normal_user["id"])

        resp = client.post(
            "/employees/assign",
            json=payload,
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["idno"] == "EMP001"
        assert body["department"] == "IT"
        assert body["user_id"] == seed_normal_user["id"]

    def test_assign_updates_user_role_to_employee(self, client, seed_admin, seed_normal_user):
        """指派後使用者角色應更新為 EMPLOYEE，登入後 role 反映新角色。"""
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        payload = _assign_employee_payload(seed_normal_user["id"])
        client.post("/employees/assign", json=payload, headers=auth_headers(admin_token))

        # 以員工帳號重新登入，驗證 role 已改為 EMPLOYEE
        user_token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        me_resp = client.get("/users/me", headers=auth_headers(user_token))
        assert me_resp.status_code == 200
        assert me_resp.json()["role"] == "EMPLOYEE"

    def test_non_admin_cannot_assign_employee(self, client, seed_normal_user, db_session):
        """一般使用者嘗試指派員工，回傳 403。"""
        # 建立第二個使用者作為被指派對象
        other = _seed_user(db_session, "other", "other@test.com", "Other123!", UserRole.NORMAL)

        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        payload = _assign_employee_payload(other["id"])

        resp = client.post(
            "/employees/assign",
            json=payload,
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_assign_nonexistent_user_returns_404(self, client, seed_admin):
        """指派不存在的使用者，回傳 404。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        payload = _assign_employee_payload("00000000-0000-0000-0000-000000000000")

        resp = client.post(
            "/employees/assign",
            json=payload,
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_assign_same_user_twice_returns_409(self, client, seed_admin, seed_normal_user):
        """重複指派同一使用者，回傳 409。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        payload = _assign_employee_payload(seed_normal_user["id"])

        # 第一次指派成功
        resp1 = client.post("/employees/assign", json=payload, headers=auth_headers(token))
        assert resp1.status_code == 200

        # 第二次指派同一使用者
        payload2 = _assign_employee_payload(seed_normal_user["id"], idno="EMP002")
        resp2 = client.post("/employees/assign", json=payload2, headers=auth_headers(token))
        assert resp2.status_code == 409

    def test_assign_duplicate_idno_returns_409(self, client, seed_admin, seed_normal_user, db_session):
        """使用重複的員工編號，回傳 409。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        # 指派第一個使用者為 EMP001
        payload = _assign_employee_payload(seed_normal_user["id"], idno="EMP001")
        resp1 = client.post("/employees/assign", json=payload, headers=auth_headers(token))
        assert resp1.status_code == 200

        # 建立第二個使用者，嘗試使用相同的 EMP001
        second_user = _seed_user(db_session, "second", "second@test.com", "Second123!", UserRole.NORMAL)
        payload2 = _assign_employee_payload(second_user["id"], idno="EMP001")
        resp2 = client.post("/employees/assign", json=payload2, headers=auth_headers(token))
        assert resp2.status_code == 409

    def test_assign_without_token_returns_401(self, client, seed_normal_user):
        """未認證存取，回傳 401。"""
        resp = client.post(
            "/employees/assign",
            json=_assign_employee_payload(seed_normal_user["id"]),
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /employees/
# ---------------------------------------------------------------------------

class TestListEmployees:
    """測試員工列表分頁端點（僅 Admin 可存取）。"""

    def test_admin_can_list_employees_empty(self, client, seed_admin):
        """沒有員工時，列表為空。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/employees/?page=1&size=10", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_admin_list_reflects_assigned_employee(self, client, seed_admin, seed_normal_user):
        """指派員工後，列表中可見該員工。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        # 指派員工
        client.post(
            "/employees/assign",
            json=_assign_employee_payload(seed_normal_user["id"]),
            headers=auth_headers(token),
        )

        # 列出員工
        resp = client.get("/employees/?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["idno"] == "EMP001"
        assert body["items"][0]["user_id"] == seed_normal_user["id"]

    def test_list_pagination(self, client, seed_admin, db_session):
        """分頁參數正常運作：page/size 符合預期。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        # 建立並指派三個員工
        for i in range(3):
            user = _seed_user(
                db_session,
                uid=f"emp_user_{i}",
                email=f"emp_{i}@test.com",
                password="Pass123!",
                role=UserRole.NORMAL,
            )
            client.post(
                "/employees/assign",
                json=_assign_employee_payload(user["id"], idno=f"EMP{i:03d}"),
                headers=auth_headers(token),
            )

        # 第一頁只取 2 筆
        resp = client.get("/employees/?page=1&size=2", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["page"] == 1

    def test_non_admin_cannot_list_employees(self, client, seed_normal_user):
        """一般使用者存取員工列表，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/employees/?page=1&size=10", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_list_returns_401(self, client):
        """未認證存取，回傳 401。"""
        resp = client.get("/employees/?page=1&size=10")
        assert resp.status_code == 401

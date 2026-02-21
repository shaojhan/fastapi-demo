"""
Integration tests: 使用者註冊、登入與受保護端點存取。

測試整個 HTTP → Router → Service → Repository → SQLite 堆疊，
僅 mock 外部服務（Email）。
"""
import pytest
from unittest.mock import AsyncMock, patch

from tests.integration.conftest import get_auth_token, auth_headers


# ---------------------------------------------------------------------------
# POST /users/create
# ---------------------------------------------------------------------------

class TestUserRegistration:
    """測試使用者註冊流程（UserService → UserRepository → DB）。"""

    _VALID_PAYLOAD = {
        "uid": "newuser",
        "pwd": "Password1!",
        "email": "newuser@test.com",
        "name": "New User",
        "birthdate": "1995-06-15",
        "description": "Hello",
        "role": "NORMAL",
    }

    def test_register_success(self, client):
        """成功建立新使用者，並呼叫 email 驗證服務。"""
        with patch(
            "app.services.EmailService.EmailService.send_verification_email",
            new=AsyncMock(),
        ):
            resp = client.post("/users/create", json=self._VALID_PAYLOAD)

        assert resp.status_code == 200
        assert "User created successfully" in resp.json()["message"]

    def test_register_duplicate_uid_returns_409(self, client, seed_normal_user):
        """使用已存在的 uid 建立使用者，回傳 409。"""
        payload = {**self._VALID_PAYLOAD, "uid": seed_normal_user["uid"], "email": "unique@test.com"}
        with patch(
            "app.services.EmailService.EmailService.send_verification_email",
            new=AsyncMock(),
        ):
            resp = client.post("/users/create", json=payload)

        assert resp.status_code == 409

    def test_register_verified_email_returns_409(self, client, seed_normal_user):
        """使用已驗證的 email 建立使用者，回傳 409。"""
        payload = {**self._VALID_PAYLOAD, "uid": "uniqueuid", "email": seed_normal_user["email"]}
        with patch(
            "app.services.EmailService.EmailService.send_verification_email",
            new=AsyncMock(),
        ):
            resp = client.post("/users/create", json=payload)

        assert resp.status_code == 409

    def test_register_unverified_email_returns_409(self, client, seed_unverified_user):
        """使用已註冊但尚未驗證的 email，回傳 409 並說明需重送驗證信。"""
        payload = {
            **self._VALID_PAYLOAD,
            "uid": "anotheruid",
            "email": seed_unverified_user["email"],
        }
        with patch(
            "app.services.EmailService.EmailService.send_verification_email",
            new=AsyncMock(),
        ):
            resp = client.post("/users/create", json=payload)

        assert resp.status_code == 409

    def test_register_invalid_payload_returns_422(self, client):
        """缺少必填欄位，回傳 422 Validation Error。"""
        resp = client.post("/users/create", json={"uid": "only_uid"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /users/login
# ---------------------------------------------------------------------------

class TestLogin:
    """測試登入流程（AuthService → UserRepository → JWT）。"""

    def test_login_with_uid_returns_token(self, client, seed_admin):
        """使用 uid 登入成功，回傳 JWT token 及使用者資訊。"""
        resp = client.post(
            "/users/login",
            data={"username": seed_admin["uid"], "password": seed_admin["password"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert "expires_in" in body
        assert body["user"]["uid"] == seed_admin["uid"]
        assert body["user"]["role"] == "ADMIN"

    def test_login_with_email_returns_token(self, client, seed_normal_user):
        """使用 email 登入成功。"""
        resp = client.post(
            "/users/login",
            data={
                "username": seed_normal_user["email"],
                "password": seed_normal_user["password"],
            },
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self, client, seed_normal_user):
        """密碼錯誤，回傳 401。"""
        resp = client.post(
            "/users/login",
            data={"username": seed_normal_user["uid"], "password": "WrongPass999!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        """帳號不存在，回傳 401。"""
        resp = client.post(
            "/users/login",
            data={"username": "ghost", "password": "anything"},
        )
        assert resp.status_code == 401

    def test_login_unverified_email_returns_403(self, client, seed_unverified_user):
        """Email 尚未驗證的帳號登入，回傳 403。"""
        resp = client.post(
            "/users/login",
            data={
                "username": seed_unverified_user["uid"],
                "password": seed_unverified_user["password"],
            },
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /users/me
# ---------------------------------------------------------------------------

class TestGetMe:
    """測試取得當前使用者資訊（JWT 認證 → UserRepository）。"""

    def test_get_me_with_valid_token(self, client, seed_normal_user):
        """有效 token 可取得自身資訊。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/users/me", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.json()
        assert body["uid"] == seed_normal_user["uid"]
        assert body["email"] == seed_normal_user["email"]
        assert body["role"] == "NORMAL"
        assert "profile" in body

    def test_get_me_without_token_returns_401(self, client):
        """未帶 token，回傳 401。"""
        resp = client.get("/users/me")
        assert resp.status_code == 401

    def test_get_me_with_invalid_token_returns_401(self, client):
        """無效 token，回傳 401。"""
        resp = client.get("/users/me", headers=auth_headers("invalid.token.here"))
        assert resp.status_code == 401

    def test_admin_get_me_shows_admin_role(self, client, seed_admin):
        """Admin 取得自身資訊，role 為 ADMIN。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/users/me", headers=auth_headers(token))

        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"


# ---------------------------------------------------------------------------
# GET /users/ (Admin only)
# ---------------------------------------------------------------------------

class TestListUsers:
    """測試使用者列表端點（僅 Admin 可存取）。"""

    def test_admin_can_list_users(self, client, seed_admin, seed_normal_user):
        """Admin 可取得使用者分頁列表，包含所有已建立的帳號。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/users/?page=1&size=10", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 2  # admin + normal user
        assert body["page"] == 1

    def test_normal_user_cannot_list_users(self, client, seed_normal_user):
        """一般使用者存取管理端點，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/users/?page=1&size=10", headers=auth_headers(token))

        assert resp.status_code == 403

    def test_list_users_unauthenticated_returns_401(self, client):
        """未認證存取，回傳 401。"""
        resp = client.get("/users/?page=1&size=10")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /users/search
# ---------------------------------------------------------------------------

class TestSearchUsers:
    """測試搜尋使用者端點（所有已登入使用者皆可使用）。"""

    def test_search_by_uid(self, client, seed_admin, seed_normal_user):
        """以 uid 關鍵字搜尋使用者。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get(
            f"/users/search?keyword={seed_normal_user['uid']}",
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 1
        uids = [item["uid"] for item in body["items"]]
        assert seed_normal_user["uid"] in uids

    def test_search_excludes_self(self, client, seed_admin, seed_normal_user):
        """搜尋結果不包含自己。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/users/search?keyword=admin", headers=auth_headers(token))

        assert resp.status_code == 200
        # admin 搜尋自己，結果中不應有 admin
        uids = [item["uid"] for item in resp.json()["items"]]
        assert seed_admin["uid"] not in uids

    def test_search_without_token_returns_401(self, client):
        """未認證搜尋，回傳 401。"""
        resp = client.get("/users/search?keyword=test")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /users/me/login-records
# ---------------------------------------------------------------------------

class TestLoginRecords:
    """測試登入紀錄端點（登入後自動記錄）。"""

    def test_my_login_records_after_login(self, client, seed_normal_user):
        """登入後可查詢到自身的登入紀錄。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/users/me/login-records", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        # 至少有一筆成功的登入記錄（剛才的登入）
        assert body["total"] >= 1
        success_records = [r for r in body["items"] if r["success"]]
        assert len(success_records) >= 1

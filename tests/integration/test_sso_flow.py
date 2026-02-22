"""
Integration tests: SSO provider management flow.

Tests the full HTTP → Router → Service → Repository → SQLite stack for:
- Public endpoint: GET /sso/providers (empty list)
- Admin CRUD: create / list / get / update / delete providers
- Activate / deactivate providers
- Global SSO config get / update
- Access control (admin-only enforcement)
"""
import pytest

from tests.integration.conftest import get_auth_token, auth_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _oidc_provider_payload(
    name: str = "Test OIDC",
    slug: str = "test-oidc",
    display_order: int = 0,
) -> dict:
    return {
        "name": name,
        "slug": slug,
        "protocol": "OIDC",
        "oidc_config": {
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "authorization_url": "https://idp.example.com/auth",
            "token_url": "https://idp.example.com/token",
            "userinfo_url": "https://idp.example.com/userinfo",
            "jwks_uri": None,
            "scopes": "openid email profile",
        },
        "attribute_mapping": {
            "email": "email",
            "name": "name",
            "external_id": "sub",
        },
        "display_order": display_order,
    }


# ---------------------------------------------------------------------------
# GET /sso/providers — public endpoint
# ---------------------------------------------------------------------------

class TestListPublicProviders:
    """測試公開的 SSO providers 端點（無需認證）。"""

    def test_list_providers_returns_empty_when_none_active(self, client):
        """沒有啟用的 provider 時，回傳空列表。"""
        resp = client.get("/sso/providers")
        assert resp.status_code == 200
        body = resp.json()
        assert "providers" in body
        assert body["providers"] == []

    def test_list_providers_only_shows_active(self, client, seed_admin):
        """只有啟用 (is_active=True) 的 provider 才出現在公開列表。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        # 建立 provider（預設未啟用）
        create_resp = client.post(
            "/sso/admin/providers",
            json=_oidc_provider_payload("Inactive Provider", "inactive-oidc"),
            headers=auth_headers(token),
        )
        assert create_resp.status_code == 200
        provider_id = create_resp.json()["id"]

        # 公開列表應為空（尚未啟用）
        public_resp = client.get("/sso/providers")
        assert public_resp.status_code == 200
        assert public_resp.json()["providers"] == []

        # 啟用後應出現在公開列表
        client.post(f"/sso/admin/providers/{provider_id}/activate", headers=auth_headers(token))

        public_resp2 = client.get("/sso/providers")
        assert public_resp2.status_code == 200
        providers = public_resp2.json()["providers"]
        assert len(providers) == 1
        assert providers[0]["slug"] == "inactive-oidc"


# ---------------------------------------------------------------------------
# GET /sso/admin/providers — admin list
# ---------------------------------------------------------------------------

class TestAdminListProviders:
    """測試管理員列表 SSO providers。"""

    def test_admin_can_list_providers_empty(self, client, seed_admin):
        """Admin 查詢空列表。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/sso/admin/providers", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "providers" in body
        assert body["providers"] == []

    def test_normal_user_cannot_list_admin_providers(self, client, seed_normal_user):
        """一般使用者無法存取管理員列表，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/sso/admin/providers", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_admin_providers(self, client):
        """未認證使用者無法存取，回傳 401。"""
        resp = client.get("/sso/admin/providers")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /sso/admin/providers — create provider
# ---------------------------------------------------------------------------

class TestAdminCreateProvider:
    """測試管理員建立 SSO provider。"""

    def test_admin_can_create_oidc_provider(self, client, seed_admin):
        """Admin 成功建立 OIDC provider。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.post(
            "/sso/admin/providers",
            json=_oidc_provider_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Test OIDC"
        assert body["slug"] == "test-oidc"
        assert body["protocol"] == "OIDC"
        assert body["is_active"] is False  # 預設未啟用
        assert "id" in body

    def test_create_provider_reflected_in_list(self, client, seed_admin):
        """建立後，provider 出現在 admin 列表。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        client.post("/sso/admin/providers", json=_oidc_provider_payload(), headers=auth_headers(token))

        list_resp = client.get("/sso/admin/providers", headers=auth_headers(token))
        assert list_resp.status_code == 200
        assert len(list_resp.json()["providers"]) == 1

    def test_non_admin_cannot_create_provider(self, client, seed_normal_user):
        """一般使用者無法建立 provider，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.post(
            "/sso/admin/providers",
            json=_oidc_provider_payload(),
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_provider(self, client):
        """未認證使用者無法建立，回傳 401。"""
        resp = client.post("/sso/admin/providers", json=_oidc_provider_payload())
        assert resp.status_code == 401

    def test_create_provider_missing_required_fields_returns_422(self, client, seed_admin):
        """缺少必填欄位，回傳 422。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.post(
            "/sso/admin/providers",
            json={"name": "No Slug"},  # missing slug, protocol
            headers=auth_headers(token),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /sso/admin/providers/{id} — get single provider
# ---------------------------------------------------------------------------

class TestAdminGetProvider:
    """測試管理員取得單一 SSO provider。"""

    def test_admin_can_get_provider(self, client, seed_admin):
        """Admin 成功取得 provider 詳情。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        create_resp = client.post(
            "/sso/admin/providers", json=_oidc_provider_payload(), headers=auth_headers(token)
        )
        provider_id = create_resp.json()["id"]

        resp = client.get(f"/sso/admin/providers/{provider_id}", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == provider_id

    def test_get_nonexistent_provider_returns_404(self, client, seed_admin):
        """取得不存在的 provider，回傳 404。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_get_provider(self, client, seed_normal_user, seed_admin):
        """一般使用者無法取得 provider 詳情，回傳 403。"""
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        create_resp = client.post(
            "/sso/admin/providers", json=_oidc_provider_payload(), headers=auth_headers(admin_token)
        )
        provider_id = create_resp.json()["id"]

        user_token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get(f"/sso/admin/providers/{provider_id}", headers=auth_headers(user_token))
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /sso/admin/providers/{id} — update provider
# ---------------------------------------------------------------------------

class TestAdminUpdateProvider:
    """測試管理員更新 SSO provider。"""

    def test_admin_can_update_provider_name(self, client, seed_admin):
        """Admin 成功更新 provider 名稱。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        create_resp = client.post(
            "/sso/admin/providers", json=_oidc_provider_payload(), headers=auth_headers(token)
        )
        provider_id = create_resp.json()["id"]

        update_resp = client.put(
            f"/sso/admin/providers/{provider_id}",
            json={"name": "Updated OIDC Provider"},
            headers=auth_headers(token),
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated OIDC Provider"

    def test_update_nonexistent_provider_returns_404(self, client, seed_admin):
        """更新不存在的 provider，回傳 404。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.put(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_update_provider(self, client, seed_normal_user):
        """一般使用者無法更新 provider，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.put(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000",
            json={"name": "Hack"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /sso/admin/providers/{id} — delete provider
# ---------------------------------------------------------------------------

class TestAdminDeleteProvider:
    """測試管理員刪除 SSO provider。"""

    def test_admin_can_delete_provider(self, client, seed_admin):
        """Admin 成功刪除 provider。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        create_resp = client.post(
            "/sso/admin/providers", json=_oidc_provider_payload(), headers=auth_headers(token)
        )
        provider_id = create_resp.json()["id"]

        del_resp = client.delete(f"/sso/admin/providers/{provider_id}", headers=auth_headers(token))
        assert del_resp.status_code == 200
        assert del_resp.json()["message"] == "SSO Provider deleted."

        # 確認已刪除
        get_resp = client.get(f"/sso/admin/providers/{provider_id}", headers=auth_headers(token))
        assert get_resp.status_code == 404

    def test_delete_nonexistent_provider_returns_404(self, client, seed_admin):
        """刪除不存在的 provider，回傳 404。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.delete(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_delete_provider(self, client, seed_normal_user):
        """一般使用者無法刪除，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.delete(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000",
            headers=auth_headers(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /sso/admin/providers/{id}/activate|deactivate
# ---------------------------------------------------------------------------

class TestAdminActivateDeactivateProvider:
    """測試啟用／停用 SSO provider。"""

    def _create_provider(self, client, token) -> str:
        resp = client.post(
            "/sso/admin/providers",
            json=_oidc_provider_payload("Toggle Provider", "toggle-oidc"),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_admin_can_activate_provider(self, client, seed_admin):
        """Admin 可以啟用 provider。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        provider_id = self._create_provider(client, token)

        resp = client.post(f"/sso/admin/providers/{provider_id}/activate", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    def test_admin_can_deactivate_provider(self, client, seed_admin):
        """Admin 可以停用 provider。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        provider_id = self._create_provider(client, token)

        # 先啟用
        client.post(f"/sso/admin/providers/{provider_id}/activate", headers=auth_headers(token))

        # 再停用
        resp = client.post(f"/sso/admin/providers/{provider_id}/deactivate", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_activate_nonexistent_provider_returns_404(self, client, seed_admin):
        """啟用不存在的 provider，回傳 404。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.post(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000/activate",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_non_admin_cannot_activate_provider(self, client, seed_normal_user):
        """一般使用者無法啟用，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.post(
            "/sso/admin/providers/00000000-0000-0000-0000-000000000000/activate",
            headers=auth_headers(token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /sso/admin/config & PUT /sso/admin/config — global SSO config
# ---------------------------------------------------------------------------

class TestAdminSSOConfig:
    """測試全域 SSO 設定讀取和更新。"""

    def test_admin_can_get_sso_config(self, client, seed_admin):
        """Admin 可以取得 SSO 設定。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.get("/sso/admin/config", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "auto_create_users" in body
        assert "enforce_sso" in body

    def test_admin_can_update_sso_config(self, client, seed_admin):
        """Admin 可以更新 SSO 設定。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        update_payload = {
            "auto_create_users": True,
            "enforce_sso": False,
            "default_role": "NORMAL",
        }
        resp = client.put("/sso/admin/config", json=update_payload, headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body["auto_create_users"] is True
        assert body["enforce_sso"] is False

    def test_normal_user_cannot_get_sso_config(self, client, seed_normal_user):
        """一般使用者無法取得 SSO 設定，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.get("/sso/admin/config", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_normal_user_cannot_update_sso_config(self, client, seed_normal_user):
        """一般使用者無法更新 SSO 設定，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        resp = client.put("/sso/admin/config", json={"auto_create_users": True}, headers=auth_headers(token))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_sso_config(self, client):
        """未認證使用者無法存取，回傳 401。"""
        assert client.get("/sso/admin/config").status_code == 401
        assert client.put("/sso/admin/config", json={}).status_code == 401

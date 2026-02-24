"""
E2E 測試：使用者帳號完整生命週期。

測試完整的使用者帳號管理旅程：
1. 使用 seed 帳號登入（模擬已完成 email 驗證的使用者）
2. 查看個人資料（/users/me）
3. 更新個人資料（姓名、生日、自我介紹）
4. 修改密碼
5. 確認新密碼可登入
6. 確認舊密碼無法登入

另包含 Admin 使用者管理旅程：
- 查看使用者列表
- 搜尋使用者
- 查看登入紀錄
"""

from unittest.mock import AsyncMock, patch

from tests.e2e.conftest import get_auth_token, auth_headers


class TestUserAccountLifecycle:
    """使用者帳號完整生命週期旅程測試。"""

    def test_profile_and_password_update_journey(self, client, seed_normal_user):
        """
        完整旅程：登入 → 查看個人資料 → 更新資料 → 修改密碼 → 新密碼登入成功。

        Step 1: 以原密碼登入
        Step 2: 查看個人資料（/users/me），確認基本欄位
        Step 3: 更新個人資料（姓名、生日、自我介紹）
        Step 4: 再次查看 /users/me，確認資料已更新
        Step 5: 修改密碼
        Step 6: 確認舊密碼無法登入（回傳 401）
        Step 7: 確認新密碼可成功登入
        Step 8: 使用新 token 仍可存取 /users/me
        """
        uid = seed_normal_user["uid"]
        user_id = seed_normal_user["id"]
        original_password = seed_normal_user["password"]
        new_password = "NewSecure456!"

        # Step 1: 以原密碼登入
        token = get_auth_token(client, uid, original_password)
        assert token is not None

        # Step 2: 查看個人資料
        me_resp = client.get("/users/me", headers=auth_headers(token))
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["uid"] == uid
        assert me_data["role"] == "NORMAL"
        assert "profile" in me_data
        assert "name" in me_data["profile"]

        # Step 3: 更新個人資料
        update_profile_resp = client.post(
            "/users/profile/update",
            json={
                "user_id": user_id,
                "name": "Updated Full Name",
                "birthdate": "1992-08-20",
                "description": "這是我更新後的自我介紹，歡迎認識我！",
            },
            headers=auth_headers(token),
        )
        assert (
            update_profile_resp.status_code == 200
        ), f"Profile update failed: {update_profile_resp.text}"

        # Step 4: 再次查看 /users/me，確認資料已更新
        me_after_resp = client.get("/users/me", headers=auth_headers(token))
        assert me_after_resp.status_code == 200
        updated_profile = me_after_resp.json()["profile"]
        assert updated_profile["name"] == "Updated Full Name"
        assert updated_profile["description"] == "這是我更新後的自我介紹，歡迎認識我！"

        # Step 5: 修改密碼
        update_pwd_resp = client.post(
            "/users/update",
            json={
                "user_id": user_id,
                "old_password": original_password,
                "new_password": new_password,
            },
            headers=auth_headers(token),
        )
        assert (
            update_pwd_resp.status_code == 200
        ), f"Password update failed: {update_pwd_resp.text}"

        # Step 6: 確認舊密碼無法登入
        old_pwd_login_resp = client.post(
            "/users/login",
            data={"username": uid, "password": original_password},
        )
        assert old_pwd_login_resp.status_code == 401

        # Step 7: 確認新密碼可成功登入
        new_login_resp = client.post(
            "/users/login",
            data={"username": uid, "password": new_password},
        )
        assert new_login_resp.status_code == 200
        new_token = new_login_resp.json()["access_token"]
        assert new_token is not None

        # Step 8: 使用新 token 仍可存取 /users/me
        final_me_resp = client.get("/users/me", headers=auth_headers(new_token))
        assert final_me_resp.status_code == 200
        assert final_me_resp.json()["uid"] == uid
        # 資料庫中的個人資料應與更新後一致
        assert final_me_resp.json()["profile"]["name"] == "Updated Full Name"

    def test_login_record_captured_after_login(self, client, seed_normal_user):
        """
        旅程：登入後系統自動記錄登入紀錄，使用者可查詢到成功的登入事件。

        Step 1: 登入
        Step 2: 查看登入紀錄，確認至少一筆成功記錄
        """
        # Step 1: 登入
        token = get_auth_token(
            client, seed_normal_user["uid"], seed_normal_user["password"]
        )

        # Step 2: 查看登入紀錄
        records_resp = client.get(
            "/users/me/login-records", headers=auth_headers(token)
        )
        assert records_resp.status_code == 200
        records_data = records_resp.json()
        assert records_data["total"] >= 1
        success_records = [r for r in records_data["items"] if r["success"]]
        assert len(success_records) >= 1

    def test_new_user_registration_and_login_journey(self, client, seed_admin):
        """
        旅程：Admin 可在使用者列表看到新建立的帳號（模擬 email 驗證後狀態）。

        Step 1: 呼叫 /users/create 建立新帳號（mock email）
        Step 2: Admin 在使用者列表中查詢新帳號
        """
        # Step 1: 建立新帳號（mock email 服務）
        with patch(
            "app.services.EmailService.EmailService.send_verification_email",
            new=AsyncMock(),
        ):
            create_resp = client.post(
                "/users/create",
                json={
                    "uid": "lifecycle_new",
                    "pwd": "NewPass123!",
                    "email": "lifecycle_new@test.com",
                    "name": "Lifecycle New User",
                    "birthdate": "1995-03-15",
                    "description": "測試帳號",
                },
            )
        assert create_resp.status_code == 200
        assert "User created successfully" in create_resp.json()["message"]

        # Step 2: Admin 在使用者列表中查詢新帳號
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        list_resp = client.get(
            "/users/?page=1&size=100", headers=auth_headers(admin_token)
        )
        assert list_resp.status_code == 200
        uids = [item["uid"] for item in list_resp.json()["items"]]
        assert "lifecycle_new" in uids

        # 確認新帳號角色為 NORMAL（防止角色注入）
        new_user_item = next(
            (item for item in list_resp.json()["items"] if item["uid"] == "lifecycle_new"),
            None,
        )
        assert new_user_item is not None
        assert new_user_item["role"] == "NORMAL"
        assert new_user_item["email_verified"] is False  # 尚未驗證 email


class TestAdminUserManagementJourney:
    """Admin 管理使用者的完整旅程。"""

    def test_admin_manages_users_journey(self, client, seed_admin, seed_normal_user):
        """
        完整旅程：查看使用者列表 → 搜尋使用者 → 查看登入紀錄。

        Step 1: Admin 查看分頁使用者列表，確認包含所有帳號
        Step 2: Admin 搜尋特定使用者，確認搜尋結果正確
        Step 3: 確認搜尋結果不包含自己（IDOR 防護）
        Step 4: Admin 查看所有登入紀錄
        Step 5: Admin 查看自己的登入紀錄
        """
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        # Step 1: Admin 查看分頁使用者列表
        list_resp = client.get(
            "/users/?page=1&size=10", headers=auth_headers(admin_token)
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 2  # admin + normal user
        assert list_data["page"] == 1
        uids_in_list = [item["uid"] for item in list_data["items"]]
        assert seed_admin["uid"] in uids_in_list
        assert seed_normal_user["uid"] in uids_in_list

        # Step 2: Admin 搜尋 normal user
        search_resp = client.get(
            f"/users/search?keyword={seed_normal_user['uid']}",
            headers=auth_headers(admin_token),
        )
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert search_data["total"] >= 1
        found_uids = [item["uid"] for item in search_data["items"]]
        assert seed_normal_user["uid"] in found_uids

        # Step 3: 確認搜尋結果不包含 admin 自己（即使 uid 關鍵字匹配）
        self_search_resp = client.get(
            f"/users/search?keyword={seed_admin['uid']}",
            headers=auth_headers(admin_token),
        )
        assert self_search_resp.status_code == 200
        self_results_uids = [item["uid"] for item in self_search_resp.json()["items"]]
        assert seed_admin["uid"] not in self_results_uids

        # Step 4: Admin 查看所有登入紀錄
        all_records_resp = client.get(
            "/users/login-records?page=1&size=10",
            headers=auth_headers(admin_token),
        )
        assert all_records_resp.status_code == 200
        all_records_data = all_records_resp.json()
        assert "items" in all_records_data
        assert all_records_data["total"] >= 1  # 至少有 admin 自己的登入記錄

        # Step 5: Admin 查看自己的登入紀錄
        my_records_resp = client.get(
            "/users/me/login-records", headers=auth_headers(admin_token)
        )
        assert my_records_resp.status_code == 200
        my_records = my_records_resp.json()
        assert my_records["total"] >= 1
        success_records = [r for r in my_records["items"] if r["success"]]
        assert len(success_records) >= 1
        # 確認紀錄屬於 admin
        assert all(r["username"] == seed_admin["uid"] for r in my_records["items"])

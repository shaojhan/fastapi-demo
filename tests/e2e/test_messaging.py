"""
E2E 測試：使用者訊息收發完整旅程。

測試跨功能的訊息系統使用者旅程：
1. 使用者 A（Admin）發送訊息給使用者 B（Normal User）
2. 使用者 B 查看未讀數量、收件匣
3. 使用者 B 閱讀訊息並回覆
4. 使用者 A 查看發件匣與訊息串
5. 使用者 B 刪除訊息後確認收件匣清空

此測試橫跨訊息的完整生命週期（發送 → 閱讀 → 回覆 → 刪除）。
"""

from tests.e2e.conftest import get_auth_token, auth_headers


class TestUserMessagingJourney:
    """使用者訊息收發完整旅程測試。"""

    def test_send_read_reply_delete_flow(self, client, seed_admin, seed_normal_user):
        """
        完整旅程：發送 → 查看未讀數 → 閱讀 → 回覆 → 查看訊息串 → 刪除。

        Step 1: Admin 發送訊息給 Normal User
        Step 2: Normal User 確認未讀數量為 1
        Step 3: Normal User 查看收件匣，確認訊息存在且未讀
        Step 4: Normal User 標記訊息為已讀
        Step 5: 確認未讀數量歸零
        Step 6: Normal User 回覆訊息
        Step 7: Admin 查看發件匣，確認訊息存在
        Step 8: Admin 查看訊息串，確認包含回覆內容
        Step 9: Normal User 刪除訊息，確認收件匣清空
        """
        normal_user_id = seed_normal_user["id"]

        # Step 1: Admin 登入並發送訊息
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        send_resp = client.post(
            "/messages/",
            json={
                "recipient_id": normal_user_id,
                "subject": "歡迎加入公司",
                "content": "歡迎您加入我們的團隊！請確認相關設備及系統存取權限。",
            },
            headers=auth_headers(admin_token),
        )
        assert send_resp.status_code == 200, f"Send message failed: {send_resp.text}"
        sent_msg = send_resp.json()
        assert sent_msg["subject"] == "歡迎加入公司"
        assert sent_msg["is_read"] is False
        message_id = sent_msg["id"]

        # Step 2: Normal User 登入，確認未讀數量為 1
        normal_token = get_auth_token(
            client, seed_normal_user["uid"], seed_normal_user["password"]
        )
        unread_resp = client.get(
            "/messages/unread-count", headers=auth_headers(normal_token)
        )
        assert unread_resp.status_code == 200
        assert unread_resp.json()["count"] == 1

        # Step 3: Normal User 查看收件匣
        inbox_resp = client.get(
            "/messages/inbox?page=1&size=10", headers=auth_headers(normal_token)
        )
        assert inbox_resp.status_code == 200
        inbox_data = inbox_resp.json()
        assert inbox_data["total"] == 1
        inbox_item = inbox_data["items"][0]
        assert inbox_item["subject"] == "歡迎加入公司"
        assert inbox_item["is_read"] is False
        assert inbox_item["sender"]["email"] == seed_admin["email"]

        # Step 4: Normal User 標記訊息為已讀
        mark_read_resp = client.put(
            f"/messages/{message_id}/read", headers=auth_headers(normal_token)
        )
        assert mark_read_resp.status_code == 200

        # Step 5: 確認未讀數量歸零
        unread_after_resp = client.get(
            "/messages/unread-count", headers=auth_headers(normal_token)
        )
        assert unread_after_resp.status_code == 200
        assert unread_after_resp.json()["count"] == 0

        # Step 6: Normal User 回覆訊息
        reply_resp = client.post(
            f"/messages/{message_id}/reply",
            json={"content": "謝謝您的歡迎！我已確認設備，期待在這裡工作。"},
            headers=auth_headers(normal_token),
        )
        assert reply_resp.status_code == 200, f"Reply failed: {reply_resp.text}"
        reply_data = reply_resp.json()
        assert reply_data["parent_id"] == message_id
        assert "謝謝" in reply_data["content"]

        # Step 7: Admin 查看發件匣，確認原始訊息存在
        sent_resp = client.get(
            "/messages/sent?page=1&size=10", headers=auth_headers(admin_token)
        )
        assert sent_resp.status_code == 200
        sent_data = sent_resp.json()
        assert sent_data["total"] == 1
        assert sent_data["items"][0]["subject"] == "歡迎加入公司"

        # Step 8: Admin 查看訊息串，確認原始訊息 + 回覆都存在
        thread_resp = client.get(
            f"/messages/thread/{message_id}", headers=auth_headers(admin_token)
        )
        assert thread_resp.status_code == 200
        thread_data = thread_resp.json()
        assert thread_data["original_message"]["id"] == message_id
        assert thread_data["total_messages"] >= 2  # 原始訊息 + 至少一條回覆
        assert len(thread_data["replies"]) >= 1
        reply_contents = [r["content"] for r in thread_data["replies"]]
        assert any("謝謝" in c for c in reply_contents)

        # Step 9: Normal User 刪除訊息，收件匣清空
        delete_resp = client.delete(
            f"/messages/{message_id}", headers=auth_headers(normal_token)
        )
        assert delete_resp.status_code == 200

        final_inbox_resp = client.get(
            "/messages/inbox?page=1&size=10", headers=auth_headers(normal_token)
        )
        assert final_inbox_resp.status_code == 200
        assert final_inbox_resp.json()["total"] == 0

    def test_batch_mark_read_flow(self, client, seed_admin, seed_normal_user):
        """
        旅程：Admin 發送多封訊息 → Normal User 批次標記已讀。
        """
        normal_user_id = seed_normal_user["id"]
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        normal_token = get_auth_token(
            client, seed_normal_user["uid"], seed_normal_user["password"]
        )

        # Admin 發送 3 封訊息
        message_ids = []
        for i in range(3):
            resp = client.post(
                "/messages/",
                json={
                    "recipient_id": normal_user_id,
                    "subject": f"通知 #{i + 1}",
                    "content": f"這是第 {i + 1} 則系統通知。",
                },
                headers=auth_headers(admin_token),
            )
            assert resp.status_code == 200
            message_ids.append(resp.json()["id"])

        # 確認未讀數量為 3
        unread_resp = client.get(
            "/messages/unread-count", headers=auth_headers(normal_token)
        )
        assert unread_resp.status_code == 200
        assert unread_resp.json()["count"] == 3

        # 批次標記所有訊息為已讀
        batch_resp = client.put(
            "/messages/batch-read",
            json={"message_ids": message_ids},
            headers=auth_headers(normal_token),
        )
        assert batch_resp.status_code == 200

        # 確認未讀數量歸零
        final_unread_resp = client.get(
            "/messages/unread-count", headers=auth_headers(normal_token)
        )
        assert final_unread_resp.status_code == 200
        assert final_unread_resp.json()["count"] == 0

    def test_get_single_message_detail(self, client, seed_admin, seed_normal_user):
        """
        旅程：發送訊息 → 收件人取得單一訊息詳情，確認欄位完整。
        """
        normal_user_id = seed_normal_user["id"]
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        normal_token = get_auth_token(
            client, seed_normal_user["uid"], seed_normal_user["password"]
        )

        # Admin 發送訊息
        send_resp = client.post(
            "/messages/",
            json={
                "recipient_id": normal_user_id,
                "subject": "詳情測試",
                "content": "請確認此訊息的完整資訊。",
            },
            headers=auth_headers(admin_token),
        )
        assert send_resp.status_code == 200
        message_id = send_resp.json()["id"]

        # Normal User 取得單一訊息詳情
        detail_resp = client.get(
            f"/messages/{message_id}", headers=auth_headers(normal_token)
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == message_id
        assert detail["subject"] == "詳情測試"
        assert detail["content"] == "請確認此訊息的完整資訊。"
        assert detail["sender"]["email"] == seed_admin["email"]
        assert detail["recipient"]["email"] == seed_normal_user["email"]
        assert "created_at" in detail

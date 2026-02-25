"""
Integration tests: HR Chat (主管審核 AI) 流程。

測試整個 HTTP → Router → Service → Repository → SQLite 堆疊：
- 驗證端點可正常存取並回傳對話 ID
- 驗證對話清單、詳情、刪除操作
- 驗證未登入時回傳 401
- OllamaClient 以 Mock 取代，避免依賴外部 LLM 服務
"""
import pytest
from unittest.mock import patch, AsyncMock

from tests.integration.conftest import get_auth_token, auth_headers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def employee_user(db_session):
    """建立一個 EMPLOYEE 身份的測試使用者。"""
    from tests.integration.conftest import _seed_user
    from app.domain.UserModel import UserRole
    return _seed_user(
        db_session,
        uid="hrmanager",
        email="hrmanager@test.com",
        password="Manager123!",
        role=UserRole.EMPLOYEE,
        name="HR Manager",
    )


def _mock_ollama_simple_reply(content: str = "您好，我是HR審核助理。"):
    """回傳一個不含 tool_calls 的 Ollama 回應 mock。"""
    return AsyncMock(return_value={
        "choices": [{"message": {"content": content}}]
    })


# ---------------------------------------------------------------------------
# POST /hr-chat/
# ---------------------------------------------------------------------------

class TestHRChatSendMessage:

    def test_send_message_creates_conversation(self, client, employee_user):
        """傳送訊息後應回傳 conversation_id 和 AI 回覆。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch(
            "app.services.ApprovalAgentService.OllamaClient"
        ) as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply(
                "您目前沒有待審申請。"
            )
            resp = client.post(
                "/hr-chat/",
                json={"message": "我有哪些待審申請？"},
                headers=auth_headers(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "conversation_id" in data
        assert data["message"] == "您目前沒有待審申請。"
        assert isinstance(data["actions_taken"], list)

    def test_send_message_continues_existing_conversation(self, client, employee_user):
        """傳入已存在的 conversation_id 應繼續同一對話。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply("第一則回覆")
            first = client.post(
                "/hr-chat/",
                json={"message": "你好"},
                headers=auth_headers(token),
            )
        assert first.status_code == 200
        conv_id = first.json()["conversation_id"]

        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply("第二則回覆")
            second = client.post(
                "/hr-chat/",
                json={"message": "繼續", "conversation_id": conv_id},
                headers=auth_headers(token),
            )
        assert second.status_code == 200
        assert second.json()["conversation_id"] == conv_id

    def test_send_message_requires_auth(self, client):
        """未登入應回傳 401。"""
        resp = client.post("/hr-chat/", json={"message": "你好"})
        assert resp.status_code == 401

    def test_send_message_wrong_conversation_id_returns_error(self, client, employee_user):
        """傳入不存在的 conversation_id 應回傳 404。"""
        import uuid
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch("app.services.ApprovalAgentService.OllamaClient"):
            resp = client.post(
                "/hr-chat/",
                json={
                    "message": "查詢",
                    "conversation_id": str(uuid.uuid4()),
                },
                headers=auth_headers(token),
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /hr-chat/conversations
# ---------------------------------------------------------------------------

class TestHRChatListConversations:

    def test_list_conversations_empty(self, client, employee_user):
        """初始狀態應回傳空列表。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])
        resp = client.get("/hr-chat/conversations", headers=auth_headers(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_conversations_after_chat(self, client, employee_user):
        """傳送訊息後對話清單應出現一筆記錄。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply()
            client.post(
                "/hr-chat/",
                json={"message": "查詢待審申請"},
                headers=auth_headers(token),
            )

        resp = client.get("/hr-chat/conversations", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["title"] == "查詢待審申請"

    def test_list_conversations_requires_auth(self, client):
        resp = client.get("/hr-chat/conversations")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /hr-chat/conversations/{id}
# ---------------------------------------------------------------------------

class TestHRChatGetConversation:

    def test_get_conversation_returns_messages(self, client, employee_user):
        """取得對話詳情應包含 user 和 assistant 訊息（排除 tool）。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply("我是助理回覆")
            post_resp = client.post(
                "/hr-chat/",
                json={"message": "列出申請"},
                headers=auth_headers(token),
            )
        conv_id = post_resp.json()["conversation_id"]

        resp = client.get(
            f"/hr-chat/conversations/{conv_id}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles
        assert "tool" not in roles

    def test_get_conversation_not_found(self, client, employee_user):
        import uuid
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])
        resp = client.get(
            f"/hr-chat/conversations/{uuid.uuid4()}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_get_conversation_requires_auth(self, client):
        import uuid
        resp = client.get(f"/hr-chat/conversations/{uuid.uuid4()}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /hr-chat/conversations/{id}
# ---------------------------------------------------------------------------

class TestHRChatDeleteConversation:

    def test_delete_conversation_success(self, client, employee_user):
        """刪除後應回傳 success，且列表中不再出現該對話。"""
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])

        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply()
            post_resp = client.post(
                "/hr-chat/",
                json={"message": "你好"},
                headers=auth_headers(token),
            )
        conv_id = post_resp.json()["conversation_id"]

        del_resp = client.delete(
            f"/hr-chat/conversations/{conv_id}",
            headers=auth_headers(token),
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        list_resp = client.get("/hr-chat/conversations", headers=auth_headers(token))
        assert list_resp.json()["total"] == 0

    def test_delete_conversation_not_found(self, client, employee_user):
        import uuid
        token = get_auth_token(client, employee_user["uid"], employee_user["password"])
        resp = client.delete(
            f"/hr-chat/conversations/{uuid.uuid4()}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_delete_conversation_requires_auth(self, client):
        import uuid
        resp = client.delete(f"/hr-chat/conversations/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_delete_other_users_conversation_returns_403(
        self, client, employee_user, seed_admin
    ):
        """刪除其他使用者的對話應回傳 403。"""
        # employee_user 建立對話
        emp_token = get_auth_token(client, employee_user["uid"], employee_user["password"])
        with patch("app.services.ApprovalAgentService.OllamaClient") as MockOllama:
            MockOllama.return_value.chat_completion = _mock_ollama_simple_reply()
            post_resp = client.post(
                "/hr-chat/",
                json={"message": "你好"},
                headers=auth_headers(emp_token),
            )
        conv_id = post_resp.json()["conversation_id"]

        # admin 嘗試刪除 employee_user 的對話
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        resp = client.delete(
            f"/hr-chat/conversations/{conv_id}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 403

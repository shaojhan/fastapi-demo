"""
Unit tests for ApprovalAgentService.

測試策略:
- Mock OllamaClient、ApprovalService、ApprovalQueryService 及 ChatUnitOfWork 系列
- 驗證 4 個工具方法的正確行為與錯誤處理
- 驗證對話管理 (get / delete) 的存取控制
- 驗證 chat() 主流程：建立新對話、既有對話驗證
"""
import asyncio
import pytest
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.services.ApprovalAgentService import ApprovalAgentService
from app.domain.ChatModel import ConversationModel, ChatMessageModel
from app.domain.ApprovalModel import (
    ApprovalRequest,
    ApprovalType,
    ApprovalStatus,
    LeaveDetail,
    LeaveType,
)
from app.exceptions.ApprovalException import (
    ApprovalNotFoundError,
    ApprovalNotAuthorizedError,
    ApprovalInvalidStatusError,
)
from app.exceptions.ChatException import (
    ConversationNotFoundError,
    ConversationAccessDeniedError,
    OllamaConnectionError,
)


# ── Test Data ──────────────────────────────────────────────────────────────

TEST_USER_ID = str(uuid4())
TEST_USERNAME = "testmanager"
TEST_CONVERSATION_ID = str(uuid4())
TEST_REQUEST_ID = str(uuid4())
APPROVER_ID = TEST_USER_ID


def _make_conversation(user_id=None, title=None):
    return ConversationModel(
        id=TEST_CONVERSATION_ID,
        user_id=user_id or TEST_USER_ID,
        title=title,
        created_at=datetime.now(),
    )


def _make_leave_request(request_id=None, approver_id=None):
    return ApprovalRequest.create_leave_request(
        requester_id="requester-1",
        detail=LeaveDetail(
            leave_type=LeaveType.ANNUAL,
            start_date=datetime(2026, 3, 10, tzinfo=UTC),
            end_date=datetime(2026, 3, 12, tzinfo=UTC),
            reason="年假",
        ),
        approver_ids=[approver_id or APPROVER_ID],
    )


def _make_approved_request():
    req = _make_leave_request()
    req.approve(APPROVER_ID, comment="核准")
    return req


# ── TestToolExecution ──────────────────────────────────────────────────────

@patch("app.services.ApprovalAgentService.OllamaClient")
@patch("app.services.ApprovalAgentService.ApprovalService")
@patch("app.services.ApprovalAgentService.ApprovalQueryService")
class TestToolExecution:
    """Tests for ApprovalAgentService tool execution methods."""

    def test_tool_list_pending_returns_requests(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        req = _make_leave_request()
        mock_qs = MockQueryService.return_value
        mock_qs.get_pending_approvals.return_value = ([req], 1)

        service = ApprovalAgentService()
        result = service._tool_list_pending(TEST_USER_ID, {"page": 1, "size": 10})

        assert result["success"] is True
        assert result["total"] == 1
        assert len(result["requests"]) == 1
        assert result["requests"][0]["type"] == "LEAVE"
        mock_qs.get_pending_approvals.assert_called_once_with(
            approver_id=TEST_USER_ID, page=1, size=10
        )

    def test_tool_list_pending_default_pagination(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_qs = MockQueryService.return_value
        mock_qs.get_pending_approvals.return_value = ([], 0)

        service = ApprovalAgentService()
        service._tool_list_pending(TEST_USER_ID, {})

        mock_qs.get_pending_approvals.assert_called_once_with(
            approver_id=TEST_USER_ID, page=1, size=10
        )

    def test_tool_list_pending_empty(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_qs = MockQueryService.return_value
        mock_qs.get_pending_approvals.return_value = ([], 0)

        service = ApprovalAgentService()
        result = service._tool_list_pending(TEST_USER_ID, {})

        assert result["success"] is True
        assert result["total"] == 0
        assert result["requests"] == []

    def test_tool_get_detail_success(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        req = _make_leave_request(request_id=TEST_REQUEST_ID)
        mock_qs = MockQueryService.return_value
        mock_qs.get_request_detail.return_value = req

        service = ApprovalAgentService()
        result = service._tool_get_detail({"request_id": req.id})

        assert result["success"] is True
        assert result["type"] == "LEAVE"
        assert result["status"] == "PENDING"
        assert "detail" in result
        assert result["current_step_order"] == 1

    def test_tool_get_detail_not_found(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_qs = MockQueryService.return_value
        mock_qs.get_request_detail.side_effect = ApprovalNotFoundError()

        service = ApprovalAgentService()
        result = service._tool_get_detail({"request_id": str(uuid4())})

        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_tool_approve_success(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        req = _make_approved_request()
        mock_as = MockApprovalService.return_value
        mock_as.approve.return_value = req

        service = ApprovalAgentService()
        result = service._tool_approve(
            TEST_USER_ID,
            {"request_id": req.id, "comment": "同意"},
        )

        assert result["success"] is True
        assert result["message"] == "申請單已核准"
        mock_as.approve.assert_called_once_with(
            request_id=req.id,
            approver_id=TEST_USER_ID,
            comment="同意",
        )

    def test_tool_approve_not_found(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_as = MockApprovalService.return_value
        mock_as.approve.side_effect = ApprovalNotFoundError()

        service = ApprovalAgentService()
        result = service._tool_approve(TEST_USER_ID, {"request_id": str(uuid4())})

        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_tool_approve_unauthorized(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_as = MockApprovalService.return_value
        mock_as.approve.side_effect = ApprovalNotAuthorizedError()

        service = ApprovalAgentService()
        result = service._tool_approve(TEST_USER_ID, {"request_id": str(uuid4())})

        assert result["success"] is False
        assert "無權" in result["error"]

    def test_tool_approve_invalid_status(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_as = MockApprovalService.return_value
        mock_as.approve.side_effect = ApprovalInvalidStatusError()

        service = ApprovalAgentService()
        result = service._tool_approve(TEST_USER_ID, {"request_id": str(uuid4())})

        assert result["success"] is False
        assert "狀態" in result["error"]

    def test_tool_reject_success(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        req = _make_leave_request()
        mock_as = MockApprovalService.return_value
        mock_as.reject.return_value = req

        service = ApprovalAgentService()
        result = service._tool_reject(
            TEST_USER_ID,
            {"request_id": req.id, "comment": "理由不充分"},
        )

        assert result["success"] is True
        assert result["message"] == "申請單已駁回"
        mock_as.reject.assert_called_once_with(
            request_id=req.id,
            approver_id=TEST_USER_ID,
            comment="理由不充分",
        )

    def test_tool_reject_not_found(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_as = MockApprovalService.return_value
        mock_as.reject.side_effect = ApprovalNotFoundError()

        service = ApprovalAgentService()
        result = service._tool_reject(TEST_USER_ID, {"request_id": str(uuid4())})

        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_tool_reject_unauthorized(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_as = MockApprovalService.return_value
        mock_as.reject.side_effect = ApprovalNotAuthorizedError()

        service = ApprovalAgentService()
        result = service._tool_reject(TEST_USER_ID, {"request_id": str(uuid4())})

        assert result["success"] is False
        assert "無權" in result["error"]

    def test_execute_tool_unknown(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        service = ApprovalAgentService()
        result = service._execute_tool(TEST_USER_ID, "nonexistent_tool", {})

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_execute_tool_catches_unexpected_exception(
        self, MockQueryService, MockApprovalService, MockOllama
    ):
        mock_qs = MockQueryService.return_value
        mock_qs.get_request_detail.side_effect = RuntimeError("unexpected DB error")

        service = ApprovalAgentService()
        result = service._execute_tool(
            TEST_USER_ID, "get_approval_detail", {"request_id": str(uuid4())}
        )

        assert result["success"] is False
        assert "unexpected DB error" in result["error"]


# ── TestConversationManagement ─────────────────────────────────────────────

class TestConversationManagement:
    """Tests for conversation management methods."""

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_get_conversations(self, mock_uow_class, MockQS, MockAS, MockOC):
        conversations = [_make_conversation()]
        mock_repo = MagicMock()
        mock_repo.get_conversations_by_user.return_value = (conversations, 1)

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        result, total = service.get_conversations(TEST_USER_ID)

        assert total == 1
        assert len(result) == 1
        mock_repo.get_conversations_by_user.assert_called_once_with(TEST_USER_ID, 1, 20)

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_filters_tool_messages(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        conv = _make_conversation()
        messages = [
            ChatMessageModel(id="1", conversation_id=TEST_CONVERSATION_ID, role="user", content="有哪些申請？", created_at=datetime.now()),
            ChatMessageModel(id="2", conversation_id=TEST_CONVERSATION_ID, role="assistant", content="以下是待審申請...", created_at=datetime.now()),
            ChatMessageModel(id="3", conversation_id=TEST_CONVERSATION_ID, role="tool", content='{"success": true}', tool_call_id="call_1", created_at=datetime.now()),
        ]
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv
        mock_repo.get_messages.return_value = messages

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        result = service.get_conversation_messages(TEST_USER_ID, TEST_CONVERSATION_ID)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_not_found(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation_messages(TEST_USER_ID, str(uuid4()))

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_get_conversation_messages_access_denied(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        conv = _make_conversation(user_id=str(uuid4()))  # 不同擁有者
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            service.get_conversation_messages(TEST_USER_ID, TEST_CONVERSATION_ID)

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatUnitOfWork")
    def test_delete_conversation_success(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        conv = _make_conversation()
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        service.delete_conversation(TEST_USER_ID, TEST_CONVERSATION_ID)

        mock_repo.delete_conversation.assert_called_once_with(TEST_CONVERSATION_ID)
        mock_uow.commit.assert_called_once()

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatUnitOfWork")
    def test_delete_conversation_not_found(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationNotFoundError):
            service.delete_conversation(TEST_USER_ID, str(uuid4()))

        mock_uow.commit.assert_not_called()

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatUnitOfWork")
    def test_delete_conversation_access_denied(
        self, mock_uow_class, MockQS, MockAS, MockOC
    ):
        conv = _make_conversation(user_id=str(uuid4()))
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            service.delete_conversation(TEST_USER_ID, TEST_CONVERSATION_ID)

        mock_repo.delete_conversation.assert_not_called()
        mock_uow.commit.assert_not_called()


# ── TestChatMethod ─────────────────────────────────────────────────────────

class TestChatMethod:
    """Tests for the main async chat() method."""

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatUnitOfWork")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_chat_new_conversation(
        self, mock_query_uow_class, mock_write_uow_class, MockQS, MockAS, MockOC
    ):
        """新對話：未傳入 conversation_id，應自動建立並回傳 AI 回覆。"""
        mock_ollama = MockOC.return_value
        mock_ollama.chat_completion = AsyncMock(return_value={
            "choices": [{"message": {"content": "您好！有什麼審核相關的問題嗎？"}}]
        })

        mock_conv = _make_conversation()
        mock_write_repo = MagicMock()
        mock_write_repo.create_conversation.return_value = mock_conv

        mock_write_uow = MagicMock()
        mock_write_uow.repo = mock_write_repo
        mock_write_uow.__enter__ = MagicMock(return_value=mock_write_uow)
        mock_write_uow.__exit__ = MagicMock(return_value=False)
        mock_write_uow_class.return_value = mock_write_uow

        mock_query_repo = MagicMock()
        mock_query_repo.get_messages.return_value = []

        mock_query_uow = MagicMock()
        mock_query_uow.repo = mock_query_repo
        mock_query_uow.__enter__ = MagicMock(return_value=mock_query_uow)
        mock_query_uow.__exit__ = MagicMock(return_value=False)
        mock_query_uow_class.return_value = mock_query_uow

        service = ApprovalAgentService()
        result = asyncio.run(
            service.chat(
                user_id=TEST_USER_ID,
                username=TEST_USERNAME,
                message="我有哪些待審申請？",
            )
        )

        assert result["conversation_id"] == TEST_CONVERSATION_ID
        assert result["message"] == "您好！有什麼審核相關的問題嗎？"
        assert result["actions_taken"] == []
        mock_write_repo.create_conversation.assert_called_once()

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_chat_existing_conversation_not_found(
        self, mock_query_uow_class, MockQS, MockAS, MockOC
    ):
        """傳入不存在的 conversation_id 應拋出 ConversationNotFoundError。"""
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = None

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_query_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationNotFoundError):
            asyncio.run(
                service.chat(
                    user_id=TEST_USER_ID,
                    username=TEST_USERNAME,
                    message="查詢申請",
                    conversation_id=str(uuid4()),
                )
            )

    @patch("app.services.ApprovalAgentService.OllamaClient")
    @patch("app.services.ApprovalAgentService.ApprovalService")
    @patch("app.services.ApprovalAgentService.ApprovalQueryService")
    @patch("app.services.ApprovalAgentService.ChatQueryUnitOfWork")
    def test_chat_existing_conversation_access_denied(
        self, mock_query_uow_class, MockQS, MockAS, MockOC
    ):
        """對話擁有者不符合時應拋出 ConversationAccessDeniedError。"""
        conv = _make_conversation(user_id=str(uuid4()))
        mock_repo = MagicMock()
        mock_repo.get_conversation.return_value = conv

        mock_uow = MagicMock()
        mock_uow.repo = mock_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_query_uow_class.return_value = mock_uow

        service = ApprovalAgentService()
        with pytest.raises(ConversationAccessDeniedError):
            asyncio.run(
                service.chat(
                    user_id=TEST_USER_ID,
                    username=TEST_USERNAME,
                    message="查詢申請",
                    conversation_id=TEST_CONVERSATION_ID,
                )
            )

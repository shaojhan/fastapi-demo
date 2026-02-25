from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger
from opentelemetry import trace

from app.domain.ChatModel import ConversationModel
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
from app.services.ApprovalService import ApprovalService, ApprovalQueryService
from app.services.OllamaClient import OllamaClient
from app.services.unitofwork.ChatUnitOfWork import ChatUnitOfWork, ChatQueryUnitOfWork


# ── Tool definitions (OpenAI function calling format) ──────────────────────

APPROVAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_pending_approvals",
            "description": "列出目前等待主管審核的申請單。可依頁碼分頁查詢。",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "頁碼，預設 1",
                    },
                    "size": {
                        "type": "integer",
                        "description": "每頁筆數，預設 10",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_approval_detail",
            "description": "取得單一申請單的完整資訊，包含申請類型（請假/報銷）、詳細內容與審核步驟。在決定審核前務必先呼叫此工具確認細節。",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "申請單的完整 UUID",
                    },
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "approve_request",
            "description": "核准一筆申請單。執行前請先確認使用者明確表示同意，並已呼叫 get_approval_detail 確認申請內容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "要核准的申請單完整 UUID",
                    },
                    "comment": {
                        "type": "string",
                        "description": "審核意見（選填）",
                    },
                },
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reject_request",
            "description": "駁回一筆申請單。執行前必須取得使用者明確的駁回指示，並建議要求填寫駁回原因。",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "要駁回的申請單完整 UUID",
                    },
                    "comment": {
                        "type": "string",
                        "description": "駁回原因（強烈建議填寫）",
                    },
                },
                "required": ["request_id"],
            },
        },
    },
]


def _build_system_prompt(username: str) -> str:
    now = datetime.now(timezone.utc).astimezone()
    return f"""你是一個人力資源審核助理，協助主管以自然語言審核員工的請假與費用報銷申請。

## 基本資訊
- 當前時間：{now.strftime('%Y-%m-%d %H:%M:%S %Z')}
- 時區：Asia/Taipei
- 主管名稱：{username}

## 行為規範

### 查詢申請
1. 當主管詢問「待審核」、「有哪些申請」等問題時，呼叫 `list_pending_approvals` 取得列表
2. 列出申請時，以結構化格式呈現：申請類型、申請人、申請日期、目前步驟
3. 顯示申請單編號時使用前 8 碼方便閱讀，但呼叫工具時一律使用完整 UUID
4. 若列表不為空，主動建議主管輸入申請單編號以查看詳情

### 查看申請詳情
5. 當主管指定某筆申請要審核時，一律先呼叫 `get_approval_detail` 取得完整資料
6. 依申請類型提供 AI 摘要與建議：
   - **請假申請**：摘要假別、天數、原因，判斷是否在合理範圍
   - **報銷申請**：摘要金額、類別、說明，判斷金額合理性
7. 提供建議（核准／駁回），但**最終決定由主管決定**，不可自行代為決定

### 核准申請
8. 只有當主管**明確表示核准**（例如：「核准」、「同意」、「通過」）時才呼叫 `approve_request`
9. 核准前再次向主管確認：「您確定要核准此 [申請類型] 申請嗎？」，等候主管確認後再執行
10. 核准成功後，告知主管結果及是否還有後續待審步驟

### 駁回申請
11. 只有當主管**明確表示駁回**（例如：「駁回」、「拒絕」、「不通過」）時才呼叫 `reject_request`
12. 駁回前詢問駁回原因，若主管未提供，提醒駁回原因有助於申請人了解改進方向
13. 駁回成功後，告知主管結果

### 通用規則
14. 使用繁體中文回覆
15. 若主管的指令不夠明確，主動詢問澄清
16. 不執行任何超出審核範圍的操作（不可建立申請單、不可取消他人申請）
17. 如果操作失敗，說明原因並建議替代方案"""


_tracer = trace.get_tracer("approval-agent")


class ApprovalAgentService:
    """AI Agent service that bridges Ollama LLM with ApprovalService."""

    def __init__(self):
        self.ollama = OllamaClient()
        self.approval_service = ApprovalService()
        self.approval_query_service = ApprovalQueryService()

    async def chat(
        self,
        user_id: str,
        username: str,
        message: str,
        conversation_id: str | None = None,
    ) -> dict:
        """
        Process a user message and return the AI response.

        Args:
            user_id: The current user's UUID
            username: The current user's display name
            message: The user's natural language message
            conversation_id: Existing conversation ID, or None to create new

        Returns:
            dict with conversation_id, message, and actions_taken
        """
        actions_taken: list[dict] = []

        # 1. Get or create conversation
        if conversation_id:
            with ChatQueryUnitOfWork() as uow:
                conv = uow.repo.get_conversation(conversation_id)
                if not conv:
                    raise ConversationNotFoundError()
                if not conv.is_owner(user_id):
                    raise ConversationAccessDeniedError()
        else:
            conv = ConversationModel.create(user_id=user_id)
            with ChatUnitOfWork() as uow:
                conv = uow.repo.create_conversation(conv)
                uow.commit()
            conversation_id = conv.id

        # 2. Load history and build messages
        with ChatQueryUnitOfWork() as uow:
            history = uow.repo.get_messages(conversation_id, limit=50)

        messages = [{"role": "system", "content": _build_system_prompt(username)}]
        for msg in history:
            entry: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                entry["content"] = msg.content
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            messages.append(entry)

        # Add the new user message
        messages.append({"role": "user", "content": message})

        # 3. Call Ollama with tool use loop
        try:
            response = await self.ollama.chat_completion(messages, tools=APPROVAL_TOOLS)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError):
            raise OllamaConnectionError()

        assistant_msg = response["choices"][0]["message"]
        tool_calls_to_save: list[dict] = []

        # Tool use loop: keep calling until no more tool_calls
        max_iterations = 10
        iteration = 0
        while assistant_msg.get("tool_calls") and iteration < max_iterations:
            iteration += 1
            tool_calls = assistant_msg["tool_calls"]
            tool_calls_to_save = tool_calls

            # Save assistant message with tool_calls
            with ChatUnitOfWork() as uow:
                uow.repo.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=assistant_msg.get("content"),
                    tool_calls=tool_calls,
                )
                uow.commit()

            messages.append({
                "role": "assistant",
                "content": assistant_msg.get("content"),
                "tool_calls": tool_calls,
            })

            # Execute each tool call
            for tool_call in tool_calls:
                func_name = tool_call["function"]["name"]
                func_args = tool_call["function"].get("arguments", "{}")
                if isinstance(func_args, str):
                    func_args = json.loads(func_args)
                call_id = tool_call.get("id", func_name)

                logger.info(f"Executing tool: {func_name} with args: {func_args}")
                result = self._execute_tool(user_id, func_name, func_args)
                actions_taken.append({
                    "tool": func_name,
                    "args": func_args,
                    "success": result.get("success", True),
                })

                result_str = json.dumps(result, ensure_ascii=False, default=str)

                # Save tool result
                with ChatUnitOfWork() as uow:
                    uow.repo.add_message(
                        conversation_id=conversation_id,
                        role="tool",
                        content=result_str,
                        tool_call_id=call_id,
                    )
                    uow.commit()

                messages.append({
                    "role": "tool",
                    "content": result_str,
                    "tool_call_id": call_id,
                })

            # Call Ollama again with tool results
            try:
                response = await self.ollama.chat_completion(messages, tools=APPROVAL_TOOLS)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError):
                raise OllamaConnectionError()

            assistant_msg = response["choices"][0]["message"]

        # 4. Save the final messages
        final_content = assistant_msg.get("content", "")

        with ChatUnitOfWork() as uow:
            # Save user message
            uow.repo.add_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
            )
            # Save final assistant response
            uow.repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_content,
            )
            # Set title from first message if new conversation
            if not conv.title and message:
                title = message[:100] if len(message) > 100 else message
                uow.repo.update_conversation_title(conversation_id, title)
            uow.commit()

        return {
            "conversation_id": conversation_id,
            "message": final_content,
            "actions_taken": actions_taken,
        }

    def _execute_tool(self, user_id: str, tool_name: str, args: dict) -> dict:
        """Execute an approval tool and return the result."""
        with _tracer.start_as_current_span(
            f"approval_agent.tool.{tool_name}",
            attributes={"tool.name": tool_name},
        ):
            try:
                match tool_name:
                    case "list_pending_approvals":
                        return self._tool_list_pending(user_id, args)
                    case "get_approval_detail":
                        return self._tool_get_detail(args)
                    case "approve_request":
                        return self._tool_approve(user_id, args)
                    case "reject_request":
                        return self._tool_reject(user_id, args)
                    case _:
                        return {"error": f"Unknown tool: {tool_name}", "success": False}
            except Exception as e:
                logger.error(f"Tool execution error [{tool_name}]: {e}")
                return {"error": str(e), "success": False}

    def _tool_list_pending(self, user_id: str, args: dict) -> dict:
        page = args.get("page", 1)
        size = args.get("size", 10)
        requests, total = self.approval_query_service.get_pending_approvals(
            approver_id=user_id,
            page=page,
            size=size,
        )
        return {
            "success": True,
            "total": total,
            "page": page,
            "size": size,
            "requests": [
                {
                    "id": r.id,
                    "type": r.type.value,
                    "status": r.status.value,
                    "requester_id": r.requester_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "current_step_order": r.current_step().step_order if r.current_step() else None,
                }
                for r in requests
            ],
        }

    def _tool_get_detail(self, args: dict) -> dict:
        try:
            request = self.approval_query_service.get_request_detail(args["request_id"])
            return {
                "success": True,
                "id": request.id,
                "type": request.type.value,
                "status": request.status.value,
                "requester_id": request.requester_id,
                "detail": request.detail_dict(),
                "steps": [
                    {
                        "step_order": s.step_order,
                        "approver_id": s.approver_id,
                        "status": s.status.value,
                        "comment": s.comment,
                        "decided_at": s.decided_at.isoformat() if s.decided_at else None,
                    }
                    for s in request.steps
                ],
                "current_step_order": request.current_step().step_order if request.current_step() else None,
                "created_at": request.created_at.isoformat() if request.created_at else None,
            }
        except ApprovalNotFoundError:
            return {"success": False, "error": "申請單不存在"}

    def _tool_approve(self, user_id: str, args: dict) -> dict:
        try:
            result = self.approval_service.approve(
                request_id=args["request_id"],
                approver_id=user_id,
                comment=args.get("comment"),
            )
            return {
                "success": True,
                "request_id": result.id,
                "new_status": result.status.value,
                "message": "申請單已核准",
                "is_fully_approved": result.status.value == "APPROVED",
            }
        except ApprovalNotFoundError:
            return {"success": False, "error": "申請單不存在"}
        except ApprovalNotAuthorizedError:
            return {"success": False, "error": "您無權審核此申請單（可能不是您的審核步驟）"}
        except ApprovalInvalidStatusError:
            return {"success": False, "error": "申請單狀態不允許此操作（可能已被處理）"}

    def _tool_reject(self, user_id: str, args: dict) -> dict:
        try:
            result = self.approval_service.reject(
                request_id=args["request_id"],
                approver_id=user_id,
                comment=args.get("comment"),
            )
            return {
                "success": True,
                "request_id": result.id,
                "new_status": result.status.value,
                "message": "申請單已駁回",
            }
        except ApprovalNotFoundError:
            return {"success": False, "error": "申請單不存在"}
        except ApprovalNotAuthorizedError:
            return {"success": False, "error": "您無權審核此申請單（可能不是您的審核步驟）"}
        except ApprovalInvalidStatusError:
            return {"success": False, "error": "申請單狀態不允許此操作（可能已被處理）"}

    # ── Conversation management ────────────────────────────────────────────

    def get_conversations(
        self, user_id: str, page: int = 1, size: int = 20
    ) -> tuple[list[ConversationModel], int]:
        with ChatQueryUnitOfWork() as uow:
            return uow.repo.get_conversations_by_user(user_id, page, size)

    def get_conversation_messages(
        self, user_id: str, conversation_id: str
    ) -> list[dict]:
        with ChatQueryUnitOfWork() as uow:
            conv = uow.repo.get_conversation(conversation_id)
            if not conv:
                raise ConversationNotFoundError()
            if not conv.is_owner(user_id):
                raise ConversationAccessDeniedError()
            messages = uow.repo.get_messages(conversation_id)
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at,
                }
                for m in messages
                if m.role in ("user", "assistant")  # Filter out tool messages
            ]

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        with ChatUnitOfWork() as uow:
            conv = uow.repo.get_conversation(conversation_id)
            if not conv:
                raise ConversationNotFoundError()
            if not conv.is_owner(user_id):
                raise ConversationAccessDeniedError()
            uow.repo.delete_conversation(conversation_id)
            uow.commit()

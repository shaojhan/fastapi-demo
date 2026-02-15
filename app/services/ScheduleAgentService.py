from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
from loguru import logger

from app.domain.ChatModel import ConversationModel
from app.exceptions.ChatException import (
    ConversationNotFoundError,
    ConversationAccessDeniedError,
    OllamaConnectionError,
)
from app.services.OllamaClient import OllamaClient
from app.services.ScheduleService import ScheduleService
from app.services.unitofwork.ChatUnitOfWork import ChatUnitOfWork, ChatQueryUnitOfWork


# ── Tool definitions (OpenAI function calling format) ──────────────────────

SCHEDULE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_schedule",
            "description": "建立一個新的排程/行程/會議。需要標題和起迄時間。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "排程標題",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "開始時間，ISO 8601 格式，例如 2025-01-15T14:00:00",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "結束時間，ISO 8601 格式，例如 2025-01-15T15:00:00",
                    },
                    "description": {
                        "type": "string",
                        "description": "排程描述（選填）",
                    },
                    "location": {
                        "type": "string",
                        "description": "地點（選填）",
                    },
                    "all_day": {
                        "type": "boolean",
                        "description": "是否為全天事件，預設 false",
                    },
                },
                "required": ["title", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_schedules",
            "description": "查詢排程列表。可依時間範圍篩選。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_from": {
                        "type": "string",
                        "description": "篩選起始時間（含），ISO 8601 格式",
                    },
                    "start_to": {
                        "type": "string",
                        "description": "篩選結束時間（含），ISO 8601 格式",
                    },
                    "page": {
                        "type": "integer",
                        "description": "頁碼，預設 1",
                    },
                    "size": {
                        "type": "integer",
                        "description": "每頁筆數，預設 20",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule",
            "description": "透過 ID 查詢單一排程的詳細資訊。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "排程的 UUID",
                    },
                },
                "required": ["schedule_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_schedule",
            "description": "修改現有排程。只需傳入要修改的欄位。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "要修改的排程 UUID",
                    },
                    "title": {
                        "type": "string",
                        "description": "新標題",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "新開始時間，ISO 8601 格式",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "新結束時間，ISO 8601 格式",
                    },
                    "description": {
                        "type": "string",
                        "description": "新描述",
                    },
                    "location": {
                        "type": "string",
                        "description": "新地點",
                    },
                },
                "required": ["schedule_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_schedule",
            "description": "刪除一個排程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "string",
                        "description": "要刪除的排程 UUID",
                    },
                },
                "required": ["schedule_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_conflicts",
            "description": "檢查指定時間範圍是否有衝突的排程。建立或修改排程前應先呼叫此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "檢查的開始時間，ISO 8601 格式",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "檢查的結束時間，ISO 8601 格式",
                    },
                    "exclude_id": {
                        "type": "string",
                        "description": "要排除的排程 UUID（修改排程時使用，排除自身）",
                    },
                },
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_available_slots",
            "description": "在指定日期的工作時間內，建議可用的空閒時段。當發現衝突時可呼叫此工具提供替代建議。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "要查詢的日期，ISO 8601 格式（例如 2025-01-15T00:00:00）",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "所需時間長度（分鐘），預設 60",
                    },
                    "work_start_hour": {
                        "type": "integer",
                        "description": "工作日開始時間（小時），預設 9",
                    },
                    "work_end_hour": {
                        "type": "integer",
                        "description": "工作日結束時間（小時），預設 18",
                    },
                },
                "required": ["date"],
            },
        },
    },
]


def _build_system_prompt(username: str) -> str:
    now = datetime.now(timezone.utc).astimezone()
    return f"""你是一個智慧排程助手，幫助使用者用自然語言管理行程。

## 基本資訊
- 當前時間：{now.strftime('%Y-%m-%d %H:%M:%S %Z')}
- 時區：Asia/Taipei
- 使用者名稱：{username}

## 行為規範
1. 使用繁體中文回覆
2. 建立排程時，如果使用者沒有明確指定時間，請主動詢問
3. **建立或修改排程前，務必先呼叫 `check_conflicts` 檢查時間衝突**
4. 如果發現衝突，請：
   - 告知使用者衝突的排程名稱和時間
   - 呼叫 `suggest_available_slots` 取得當天可用時段
   - 列出 2-3 個替代時段供使用者選擇
   - 等使用者確認後再建立排程
5. 執行刪除操作前，請先確認使用者的意圖
6. 查詢結果請以清晰易讀的格式呈現
7. 如果操作成功，簡要說明結果；如果失敗，說明原因並建議替代方案
8. 當使用者說「明天」、「下週一」等相對時間時，請根據當前時間正確計算日期
9. 時間格式使用 ISO 8601，但回覆使用者時用人類可讀的格式"""


class ScheduleAgentService:
    """AI Agent service that bridges Ollama LLM with ScheduleService."""

    def __init__(self):
        self.ollama = OllamaClient()
        self.schedule_service = ScheduleService()

    def _is_google_connected(self) -> bool:
        """Check if Google Calendar is connected."""
        status = self.schedule_service.get_google_status()
        return status.get("connected", False)

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
            response = await self.ollama.chat_completion(messages, tools=SCHEDULE_TOOLS)
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
                response = await self.ollama.chat_completion(messages, tools=SCHEDULE_TOOLS)
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
        """Execute a schedule tool and return the result."""
        try:
            match tool_name:
                case "create_schedule":
                    return self._tool_create_schedule(user_id, args)
                case "list_schedules":
                    return self._tool_list_schedules(args)
                case "get_schedule":
                    return self._tool_get_schedule(args)
                case "update_schedule":
                    return self._tool_update_schedule(user_id, args)
                case "delete_schedule":
                    return self._tool_delete_schedule(user_id, args)
                case "check_conflicts":
                    return self._tool_check_conflicts(args)
                case "suggest_available_slots":
                    return self._tool_suggest_available_slots(args)
                case _:
                    return {"error": f"Unknown tool: {tool_name}", "success": False}
        except Exception as e:
            logger.error(f"Tool execution error [{tool_name}]: {e}")
            return {"error": str(e), "success": False}

    def _tool_create_schedule(self, user_id: str, args: dict) -> dict:
        schedule = self.schedule_service.create_schedule(
            creator_id=user_id,
            title=args["title"],
            start_time=datetime.fromisoformat(args["start_time"]),
            end_time=datetime.fromisoformat(args["end_time"]),
            description=args.get("description"),
            location=args.get("location"),
            all_day=args.get("all_day", False),
            sync_to_google=self._is_google_connected(),
        )
        return {
            "success": True,
            "schedule_id": schedule.id,
            "title": schedule.title,
            "start_time": schedule.start_time.isoformat(),
            "end_time": schedule.end_time.isoformat(),
            "description": schedule.description,
            "location": schedule.location,
        }

    def _tool_list_schedules(self, args: dict) -> dict:
        start_from = None
        start_to = None
        if args.get("start_from"):
            start_from = datetime.fromisoformat(args["start_from"])
        if args.get("start_to"):
            start_to = datetime.fromisoformat(args["start_to"])

        schedules, total = self.schedule_service.list_schedules(
            page=args.get("page", 1),
            size=args.get("size", 20),
            start_from=start_from,
            start_to=start_to,
        )
        return {
            "success": True,
            "total": total,
            "schedules": [
                {
                    "id": s.id,
                    "title": s.title,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "description": s.description,
                    "location": s.location,
                    "all_day": s.all_day,
                }
                for s in schedules
            ],
        }

    def _tool_get_schedule(self, args: dict) -> dict:
        schedule = self.schedule_service.get_schedule(args["schedule_id"])
        return {
            "success": True,
            "id": schedule.id,
            "title": schedule.title,
            "start_time": schedule.start_time.isoformat(),
            "end_time": schedule.end_time.isoformat(),
            "description": schedule.description,
            "location": schedule.location,
            "all_day": schedule.all_day,
            "timezone": schedule.timezone,
            "creator_id": schedule.creator_id,
        }

    def _tool_update_schedule(self, user_id: str, args: dict) -> dict:
        kwargs: dict[str, Any] = {}
        if "title" in args:
            kwargs["title"] = args["title"]
        if "description" in args:
            kwargs["description"] = args["description"]
        if "location" in args:
            kwargs["location"] = args["location"]
        if "start_time" in args:
            kwargs["start_time"] = datetime.fromisoformat(args["start_time"])
        if "end_time" in args:
            kwargs["end_time"] = datetime.fromisoformat(args["end_time"])

        schedule = self.schedule_service.update_schedule(
            user_id=user_id,
            schedule_id=args["schedule_id"],
            sync_to_google=self._is_google_connected(),
            **kwargs,
        )
        return {
            "success": True,
            "schedule_id": schedule.id,
            "title": schedule.title,
            "start_time": schedule.start_time.isoformat(),
            "end_time": schedule.end_time.isoformat(),
        }

    def _tool_delete_schedule(self, user_id: str, args: dict) -> dict:
        self.schedule_service.delete_schedule(
            user_id=user_id,
            schedule_id=args["schedule_id"],
        )
        return {"success": True, "message": "排程已刪除"}

    def _tool_check_conflicts(self, args: dict) -> dict:
        start_time = datetime.fromisoformat(args["start_time"])
        end_time = datetime.fromisoformat(args["end_time"])
        exclude_id = args.get("exclude_id")

        conflicts = self.schedule_service.check_conflicts(
            start_time=start_time,
            end_time=end_time,
            exclude_id=exclude_id,
        )
        return {
            "success": True,
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": [
                {
                    "id": s.id,
                    "title": s.title,
                    "start_time": s.start_time.isoformat(),
                    "end_time": s.end_time.isoformat(),
                    "location": s.location,
                }
                for s in conflicts
            ],
        }

    def _tool_suggest_available_slots(self, args: dict) -> dict:
        date = datetime.fromisoformat(args["date"])
        duration_minutes = args.get("duration_minutes", 60)
        work_start_hour = args.get("work_start_hour", 9)
        work_end_hour = args.get("work_end_hour", 18)

        slots = self.schedule_service.suggest_available_slots(
            date=date,
            duration_minutes=duration_minutes,
            work_start_hour=work_start_hour,
            work_end_hour=work_end_hour,
        )
        return {
            "success": True,
            "available_slots": slots,
            "total_slots": len(slots),
        }

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

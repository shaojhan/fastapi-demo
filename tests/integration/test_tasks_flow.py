"""
Integration tests: Background task monitoring endpoints.

Tests the full HTTP → Router stack for:
- GET /tasks/status/{task_id}  — PENDING / PROGRESS / SUCCESS / FAILURE
- DELETE /tasks/cancel/{task_id} — cancel a running task
- GET /tasks/add — demo enqueue endpoint

Celery is mocked so no broker/worker is needed.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# GET /tasks/status/{task_id}
# ---------------------------------------------------------------------------

class TestGetTaskStatus:
    """測試取得背景任務狀態。"""

    def _mock_async_result(self, status: str, info=None, result=None):
        """建立模擬的 Celery AsyncResult 物件。"""
        mock_result = MagicMock()
        mock_result.status = status
        mock_result.info = info
        mock_result.result = result
        return mock_result

    def test_pending_task_status(self, client):
        """PENDING 狀態：無進度資訊。"""
        mock_result = self._mock_async_result("PENDING")

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/fake-task-id-123")

        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "fake-task-id-123"
        assert body["status"] == "PENDING"
        assert body["progress"] is None
        assert body["result"] is None
        assert body["error"] is None

    def test_progress_task_status(self, client):
        """PROGRESS 狀態：包含進度資訊。"""
        progress_meta = {
            "current": 5,
            "total": 10,
            "percent": 50.0,
            "current_idno": "EMP005",
        }
        mock_result = self._mock_async_result("PROGRESS", info=progress_meta)

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/progress-task-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "PROGRESS"
        assert body["progress"]["current"] == 5
        assert body["progress"]["total"] == 10
        assert body["progress"]["percent"] == 50.0
        assert body["progress"]["current_idno"] == "EMP005"

    def test_success_task_status(self, client):
        """SUCCESS 狀態：包含結果。"""
        task_result = {"imported": 10, "failed": 0}
        mock_result = self._mock_async_result("SUCCESS", result=task_result)
        mock_result.result = task_result

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/success-task-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "SUCCESS"
        assert body["result"] == task_result
        assert body["progress"] is None

    def test_failure_task_status(self, client):
        """FAILURE 狀態：包含錯誤訊息。"""
        mock_result = self._mock_async_result("FAILURE", info=ValueError("Something went wrong"))

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/failed-task-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "FAILURE"
        assert body["error"] is not None
        assert "Something went wrong" in body["error"]
        assert body["progress"] is None

    def test_failure_task_with_no_info(self, client):
        """FAILURE 狀態但 info 為 None：回傳 'Unknown error'。"""
        mock_result = self._mock_async_result("FAILURE", info=None)

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/no-info-task")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "FAILURE"
        assert body["error"] == "Unknown error"

    def test_started_task_status(self, client):
        """STARTED 狀態：無進度和結果。"""
        mock_result = self._mock_async_result("STARTED")

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/started-task-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "STARTED"
        assert body["progress"] is None
        assert body["result"] is None
        assert body["error"] is None

    def test_revoked_task_status(self, client):
        """REVOKED 狀態：無進度和結果。"""
        mock_result = self._mock_async_result("REVOKED")

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.get("/tasks/status/revoked-task-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "REVOKED"
        assert body["progress"] is None


# ---------------------------------------------------------------------------
# DELETE /tasks/cancel/{task_id}
# ---------------------------------------------------------------------------

class TestCancelTask:
    """測試取消背景任務。"""

    def test_cancel_task_returns_cancelled_true(self, client):
        """取消任務回傳 cancelled=True。"""
        mock_result = MagicMock()
        mock_result.revoke = MagicMock()

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            resp = client.delete("/tasks/cancel/task-to-cancel")

        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "task-to-cancel"
        assert body["cancelled"] is True

    def test_cancel_calls_revoke_with_sigterm(self, client):
        """確認 revoke 以 SIGTERM 訊號觸發。"""
        mock_result = MagicMock()

        with patch("app.router.TasksRouter.AsyncResult", return_value=mock_result):
            client.delete("/tasks/cancel/sigterm-task")

        mock_result.revoke.assert_called_once_with(terminate=True, signal="SIGTERM")


# ---------------------------------------------------------------------------
# GET /tasks/add — demo enqueue endpoint
# ---------------------------------------------------------------------------

class TestEnqueueDemoTask:
    """測試示範排程端點。"""

    def test_enqueue_demo_task_returns_task_id(self, client):
        """呼叫 demo 端點會回傳 task_id。"""
        mock_task = MagicMock()
        mock_task.id = "demo-task-uuid-123"

        with patch("app.router.TasksRouter.very_long_task") as mock_very_long_task:
            mock_very_long_task.delay.return_value = mock_task
            resp = client.get("/tasks/add")

        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body
        assert body["task_id"] == "demo-task-uuid-123"

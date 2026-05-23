"""
Unit tests for WorkflowUnitOfWork.

測試策略: Mock engine 和 SpiffWorkflow，驗證 context manager 行為。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.WorkflowUnitOfWork import WorkflowUnitOfWork
from app.repositories.sqlalchemy.WorkflowRepository import WorkflowRepository


class TestWorkflowUnitOfWork:
    @patch("app.services.unitofwork.base.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = WorkflowUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, WorkflowRepository)
        uow.session.close()

    @patch("app.services.unitofwork.base.engine")
    def test_exit_rolls_back_uncommitted_on_success(self, mock_engine):
        uow = WorkflowUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        # New contract: __exit__ rolls back uncommitted work; no auto-commit.
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @patch("app.services.unitofwork.base.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = WorkflowUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()

    @patch("app.services.unitofwork.base.engine")
    def test_has_serializer(self, mock_engine):
        """測試 WorkflowUnitOfWork 初始化時建立 serializer"""
        uow = WorkflowUnitOfWork()
        assert uow.serializer is not None

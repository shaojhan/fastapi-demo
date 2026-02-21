"""
Unit tests for EmployeeUnitOfWork and EmployeeQueryUnitOfWork.

測試策略:
- Mock engine 避免真實 DB 連線
- 驗證 context manager 的 commit/rollback/close 行為
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.unitofwork.EmployeeUnitOfWork import EmployeeUnitOfWork, EmployeeQueryUnitOfWork
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository, EmployeeQueryRepository


class TestEmployeeUnitOfWork:
    """測試 EmployeeUnitOfWork 寫入交易管理"""

    @patch("app.services.unitofwork.EmployeeUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = EmployeeUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, EmployeeRepository)
        uow.session.close()

    @patch("app.services.unitofwork.EmployeeUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = EmployeeUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.EmployeeUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = EmployeeUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestEmployeeQueryUnitOfWork:
    """測試 EmployeeQueryUnitOfWork 唯讀查詢管理"""

    @patch("app.services.unitofwork.EmployeeUnitOfWork.engine")
    def test_enter_creates_query_repo(self, mock_engine):
        uow = EmployeeQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.query_repo, EmployeeQueryRepository)
        uow.session.close()

    @patch("app.services.unitofwork.EmployeeUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = EmployeeQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

"""
Unit tests for ApprovalUnitOfWork and ApprovalQueryUnitOfWork.
Tests transaction management and repository initialization.

測試策略:
- Mock engine 避免真實資料庫連線
- 驗證 __enter__ 正確初始化 repo 和 employee_repo
- 驗證 __exit__ 的 commit/rollback/close 行為
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.unitofwork.ApprovalUnitOfWork import ApprovalUnitOfWork, ApprovalQueryUnitOfWork
from app.repositories.sqlalchemy.ApprovalRepository import ApprovalRepository, ApprovalQueryRepository
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository


class TestApprovalUnitOfWork:
    """測試 ApprovalUnitOfWork 寫入交易管理"""

    @patch("app.services.unitofwork.ApprovalUnitOfWork.engine")
    def test_enter_creates_repos(self, mock_engine):
        """測試進入 context manager 時建立 approval 和 employee repositories"""
        uow = ApprovalUnitOfWork()
        result = uow.__enter__()

        assert result is uow
        assert isinstance(uow.repo, ApprovalRepository)
        assert isinstance(uow.employee_repo, EmployeeRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ApprovalUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        """測試正常退出時自動 commit"""
        uow = ApprovalUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(None, None, None)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.ApprovalUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        """測試異常退出時自動 rollback"""
        uow = ApprovalUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(ValueError, ValueError("error"), None)

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestApprovalQueryUnitOfWork:
    """測試 ApprovalQueryUnitOfWork 唯讀查詢管理"""

    @patch("app.services.unitofwork.ApprovalUnitOfWork.engine")
    def test_enter_creates_query_repo(self, mock_engine):
        """測試進入 context manager 時建立 query repository"""
        uow = ApprovalQueryUnitOfWork()
        result = uow.__enter__()

        assert result is uow
        assert isinstance(uow.repo, ApprovalQueryRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ApprovalUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        """測試退出時只關閉 session"""
        uow = ApprovalQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(None, None, None)

        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

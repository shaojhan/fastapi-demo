"""
Unit tests for UserUnitOfWork and UserQueryUnitOfWork.
Tests the transaction management and context manager behavior.

測試策略:
- Mock SessionLocal 和 Session 物件
- 驗證正常流程: __enter__ 初始化 session/repo, __exit__ commit/close
- 驗證異常流程: __exit__ rollback/close
- 驗證手動 commit/rollback
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.unitofwork.UserUnitOfWork import UserUnitOfWork, UserQueryUnitOfWork
from app.repositories.sqlalchemy.UserRepository import UserRepository, UserQueryRepository


class TestUserUnitOfWork:
    """測試 UserUnitOfWork 寫入交易管理"""

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_enter_creates_session_and_repo(self, mock_engine):
        """測試進入 context manager 時建立 session 和 repository"""
        uow = UserUnitOfWork()
        result = uow.__enter__()

        assert result is uow
        assert hasattr(uow, "session")
        assert hasattr(uow, "repo")
        assert isinstance(uow.repo, UserRepository)
        uow.session.close()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        """測試正常退出時自動 commit"""
        uow = UserUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(None, None, None)

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        """測試異常退出時自動 rollback"""
        uow = UserUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(ValueError, ValueError("error"), None)

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_manual_commit(self, mock_engine):
        """測試手動 commit"""
        uow = UserUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.commit()

        mock_session.commit.assert_called_once()
        uow.session.close()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_manual_rollback(self, mock_engine):
        """測試手動 rollback"""
        uow = UserUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.rollback()

        mock_session.rollback.assert_called_once()
        uow.session.close()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_context_manager_usage(self, mock_engine):
        """測試完整 context manager 流程"""
        with UserUnitOfWork() as uow:
            mock_session = MagicMock()
            uow.session = mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestUserQueryUnitOfWork:
    """測試 UserQueryUnitOfWork 唯讀查詢管理"""

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_enter_creates_session_and_query_repo(self, mock_engine):
        """測試進入 context manager 時建立 session 和 query repository"""
        uow = UserQueryUnitOfWork()
        result = uow.__enter__()

        assert result is uow
        assert hasattr(uow, "session")
        assert hasattr(uow, "query_repo")
        assert isinstance(uow.query_repo, UserQueryRepository)
        uow.session.close()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_exit_closes_session_without_commit(self, mock_engine):
        """測試退出時只關閉 session，不 commit"""
        uow = UserQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session

        uow.__exit__(None, None, None)

        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

    @patch("app.services.unitofwork.UserUnitOfWork.engine")
    def test_context_manager_usage(self, mock_engine):
        """測試完整 context manager 流程"""
        with UserQueryUnitOfWork() as uow:
            mock_session = MagicMock()
            uow.session = mock_session

        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

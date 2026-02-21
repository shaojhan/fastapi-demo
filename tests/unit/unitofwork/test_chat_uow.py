"""
Unit tests for ChatUnitOfWork and ChatQueryUnitOfWork.

測試策略: Mock engine，驗證 context manager 行為。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.ChatUnitOfWork import ChatUnitOfWork, ChatQueryUnitOfWork
from app.repositories.sqlalchemy.ChatRepository import ChatRepository


class TestChatUnitOfWork:
    @patch("app.services.unitofwork.ChatUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = ChatUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, ChatRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ChatUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = ChatUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.ChatUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = ChatUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()


class TestChatQueryUnitOfWork:
    @patch("app.services.unitofwork.ChatUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = ChatQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, ChatRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ChatUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = ChatQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

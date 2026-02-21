"""
Unit tests for MessageUnitOfWork and MessageQueryUnitOfWork.

測試策略: Mock engine，驗證 context manager 行為。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.MessageUnitOfWork import MessageUnitOfWork, MessageQueryUnitOfWork
from app.repositories.sqlalchemy.MessageRepository import MessageRepository, MessageQueryRepository


class TestMessageUnitOfWork:
    @patch("app.services.unitofwork.MessageUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = MessageUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, MessageRepository)
        uow.session.close()

    @patch("app.services.unitofwork.MessageUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = MessageUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.MessageUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = MessageUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()


class TestMessageQueryUnitOfWork:
    @patch("app.services.unitofwork.MessageUnitOfWork.engine")
    def test_enter_creates_repos(self, mock_engine):
        uow = MessageQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.query_repo, MessageQueryRepository)
        assert isinstance(uow.repo, MessageRepository)
        uow.session.close()

    @patch("app.services.unitofwork.MessageUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = MessageQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

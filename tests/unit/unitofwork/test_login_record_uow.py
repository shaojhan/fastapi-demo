"""
Unit tests for LoginRecordUnitOfWork and LoginRecordQueryUnitOfWork.

測試策略: Mock engine，驗證 context manager 行為。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.LoginRecordUnitOfWork import LoginRecordUnitOfWork, LoginRecordQueryUnitOfWork
from app.repositories.sqlalchemy.LoginRecordRepository import LoginRecordRepository, LoginRecordQueryRepository


class TestLoginRecordUnitOfWork:
    @patch("app.services.unitofwork.LoginRecordUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = LoginRecordUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, LoginRecordRepository)
        uow.session.close()

    @patch("app.services.unitofwork.LoginRecordUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = LoginRecordUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.LoginRecordUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = LoginRecordUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()


class TestLoginRecordQueryUnitOfWork:
    @patch("app.services.unitofwork.LoginRecordUnitOfWork.engine")
    def test_enter_creates_query_repo(self, mock_engine):
        uow = LoginRecordQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.query_repo, LoginRecordQueryRepository)
        uow.session.close()

    @patch("app.services.unitofwork.LoginRecordUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = LoginRecordQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

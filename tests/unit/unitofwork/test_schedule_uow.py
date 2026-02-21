"""
Unit tests for ScheduleUnitOfWork and ScheduleQueryUnitOfWork.

測試策略: Mock engine，驗證 context manager 及雙 repo 初始化。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.ScheduleUnitOfWork import ScheduleUnitOfWork, ScheduleQueryUnitOfWork
from app.repositories.sqlalchemy.ScheduleRepository import ScheduleRepository, GoogleCalendarConfigRepository


class TestScheduleUnitOfWork:
    @patch("app.services.unitofwork.ScheduleUnitOfWork.engine")
    def test_enter_creates_repos(self, mock_engine):
        uow = ScheduleUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, ScheduleRepository)
        assert isinstance(uow.google_config_repo, GoogleCalendarConfigRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ScheduleUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = ScheduleUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.ScheduleUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = ScheduleUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()


class TestScheduleQueryUnitOfWork:
    @patch("app.services.unitofwork.ScheduleUnitOfWork.engine")
    def test_enter_creates_repos(self, mock_engine):
        uow = ScheduleQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, ScheduleRepository)
        assert isinstance(uow.google_config_repo, GoogleCalendarConfigRepository)
        uow.session.close()

    @patch("app.services.unitofwork.ScheduleUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = ScheduleQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

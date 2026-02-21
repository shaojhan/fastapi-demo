"""
Unit tests for SSOUnitOfWork and SSOQueryUnitOfWork.

測試策略: Mock engine，驗證 context manager 及多 repo 初始化。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.SSOUnitOfWork import SSOUnitOfWork, SSOQueryUnitOfWork
from app.repositories.sqlalchemy.SSORepository import SSOProviderRepository, SSOConfigRepository, SSOUserLinkRepository
from app.repositories.sqlalchemy.UserRepository import UserRepository


class TestSSOUnitOfWork:
    @patch("app.services.unitofwork.SSOUnitOfWork.engine")
    def test_enter_creates_all_repos(self, mock_engine):
        uow = SSOUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.provider_repo, SSOProviderRepository)
        assert isinstance(uow.config_repo, SSOConfigRepository)
        assert isinstance(uow.user_link_repo, SSOUserLinkRepository)
        assert isinstance(uow.user_repo, UserRepository)
        uow.session.close()

    @patch("app.services.unitofwork.SSOUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = SSOUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.SSOUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = SSOUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()


class TestSSOQueryUnitOfWork:
    @patch("app.services.unitofwork.SSOUnitOfWork.engine")
    def test_enter_creates_repos(self, mock_engine):
        uow = SSOQueryUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.provider_repo, SSOProviderRepository)
        assert isinstance(uow.config_repo, SSOConfigRepository)
        assert isinstance(uow.user_link_repo, SSOUserLinkRepository)
        uow.session.close()

    @patch("app.services.unitofwork.SSOUnitOfWork.engine")
    def test_exit_closes_without_commit(self, mock_engine):
        uow = SSOQueryUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

"""
Unit tests for the shared BaseUnitOfWork / BaseQueryUnitOfWork.

Transaction contract:
- Write UoW requires an explicit ``commit()``.
- ``__exit__`` always rolls back (a no-op once ``commit()`` ran) and then closes.
- Query UoW never commits — it only closes.
"""
from unittest.mock import MagicMock, patch

from app.services.unitofwork.base import BaseQueryUnitOfWork, BaseUnitOfWork


class _DummyUnitOfWork(BaseUnitOfWork):
    def _setup_repositories(self, session):
        self.repo = object()


class _DummyQueryUnitOfWork(BaseQueryUnitOfWork):
    def _setup_repositories(self, session):
        self.repo = object()


class TestBaseUnitOfWork:
    @patch("app.services.unitofwork.base.engine")
    def test_enter_creates_session_and_repos(self, mock_engine):
        uow = _DummyUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert hasattr(uow, "session")
        assert hasattr(uow, "repo")
        uow.session.close()

    @patch("app.services.unitofwork.base.engine")
    def test_exit_rolls_back_uncommitted_on_success(self, mock_engine):
        uow = _DummyUnitOfWork()
        uow.__enter__()
        uow.session = MagicMock()

        uow.__exit__(None, None, None)

        uow.session.rollback.assert_called_once()
        uow.session.commit.assert_not_called()
        uow.session.close.assert_called_once()

    @patch("app.services.unitofwork.base.engine")
    def test_exit_rolls_back_on_exception(self, mock_engine):
        uow = _DummyUnitOfWork()
        uow.__enter__()
        uow.session = MagicMock()

        uow.__exit__(ValueError, ValueError("boom"), None)

        uow.session.rollback.assert_called_once()
        uow.session.close.assert_called_once()

    @patch("app.services.unitofwork.base.engine")
    def test_explicit_commit_then_exit(self, mock_engine):
        uow = _DummyUnitOfWork()
        uow.__enter__()
        uow.session = MagicMock()

        uow.commit()
        uow.__exit__(None, None, None)

        # commit() persists; the trailing rollback on exit is a harmless no-op.
        uow.session.commit.assert_called_once()
        uow.session.rollback.assert_called_once()
        uow.session.close.assert_called_once()

    @patch("app.services.unitofwork.base.engine")
    def test_manual_rollback(self, mock_engine):
        uow = _DummyUnitOfWork()
        uow.__enter__()
        uow.session = MagicMock()

        uow.rollback()

        uow.session.rollback.assert_called_once()
        uow.session.close()

    @patch("app.services.unitofwork.base.engine")
    def test_setup_repositories_must_be_implemented(self, mock_engine):
        class _Incomplete(BaseUnitOfWork):
            pass

        try:
            _Incomplete().__enter__()
            raised = False
        except NotImplementedError:
            raised = True
        assert raised


class TestBaseQueryUnitOfWork:
    @patch("app.services.unitofwork.base.engine")
    def test_exit_closes_without_commit_or_rollback(self, mock_engine):
        uow = _DummyQueryUnitOfWork()
        uow.__enter__()
        uow.session = MagicMock()

        uow.__exit__(None, None, None)

        uow.session.close.assert_called_once()
        uow.session.commit.assert_not_called()
        uow.session.rollback.assert_not_called()

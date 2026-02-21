"""
Unit tests for KafkaUnitOfWork.

測試策略: Mock engine，驗證 context manager 行為。
注意: KafkaUnitOfWork 不會在正常退出時自動 commit（需手動），
      但會在異常時 rollback。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.KafkaUnitOfWork import KafkaUnitOfWork
from app.repositories.sqlalchemy.KafkaRepository import KafkaMessageRepository


class TestKafkaUnitOfWork:
    @patch("app.services.unitofwork.KafkaUnitOfWork.engine")
    def test_enter_creates_repo(self, mock_engine):
        uow = KafkaUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.repo, KafkaMessageRepository)
        uow.session.close()

    @patch("app.services.unitofwork.KafkaUnitOfWork.engine")
    def test_exit_does_not_auto_commit(self, mock_engine):
        """KafkaUnitOfWork 正常退出時不會自動 commit"""
        uow = KafkaUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.KafkaUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = KafkaUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.KafkaUnitOfWork.engine")
    def test_manual_commit(self, mock_engine):
        uow = KafkaUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.commit()
        mock_session.commit.assert_called_once()
        uow.session.close()

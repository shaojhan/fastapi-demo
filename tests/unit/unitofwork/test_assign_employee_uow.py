"""
Unit tests for AssignEmployeeUnitOfWork.

測試策略: Mock engine，驗證跨聚合根的交易管理和雙 repo 初始化。
"""
from unittest.mock import patch, MagicMock

from app.services.unitofwork.AssignEmployeeUnitOfWork import AssignEmployeeUnitOfWork
from app.repositories.sqlalchemy.UserRepository import UserRepository
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository


class TestAssignEmployeeUnitOfWork:
    @patch("app.services.unitofwork.AssignEmployeeUnitOfWork.engine")
    def test_enter_creates_both_repos(self, mock_engine):
        """測試進入時建立 user 和 employee 兩個 repository"""
        uow = AssignEmployeeUnitOfWork()
        result = uow.__enter__()
        assert result is uow
        assert isinstance(uow.user_repo, UserRepository)
        assert isinstance(uow.employee_repo, EmployeeRepository)
        uow.session.close()

    @patch("app.services.unitofwork.AssignEmployeeUnitOfWork.engine")
    def test_exit_commits_on_success(self, mock_engine):
        uow = AssignEmployeeUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(None, None, None)
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.AssignEmployeeUnitOfWork.engine")
    def test_exit_rollbacks_on_exception(self, mock_engine):
        uow = AssignEmployeeUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.__exit__(ValueError, ValueError("err"), None)
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("app.services.unitofwork.AssignEmployeeUnitOfWork.engine")
    def test_manual_commit(self, mock_engine):
        uow = AssignEmployeeUnitOfWork()
        uow.__enter__()
        mock_session = MagicMock()
        uow.session = mock_session
        uow.commit()
        mock_session.commit.assert_called_once()
        uow.session.close()

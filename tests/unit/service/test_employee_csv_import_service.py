"""
Unit tests for EmployeeService.batch_import_employees and _import_single_employee.
"""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.EmployeeService import EmployeeService
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.EmployeeModel import EmployeeModel, Department


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_IDNO = "EMP001"
TEST_DEPARTMENT = Department.IT


def _make_valid_row(idno="EMP001", department="IT", email="john@example.com", uid="john", role_id=""):
    return {
        'idno': idno,
        'department': department,
        'email': email,
        'uid': uid,
        'role_id': role_id,
    }


def _make_user_model(user_id=None, uid="john", email="john@example.com", role=UserRole.NORMAL) -> UserModel:
    return UserModel.reconstitute(
        id=user_id or TEST_USER_ID,
        uid=uid,
        email=email,
        hashed_password="hashed",
        profile=DomainProfile(name="Test", birthdate=None, description=None),
        role=role,
        email_verified=True,
    )


def _make_employee_model(user_id=None, idno=TEST_IDNO) -> EmployeeModel:
    return EmployeeModel(
        id=1,
        idno=idno,
        department=TEST_DEPARTMENT,
        user_id=user_id or TEST_USER_ID,
        role=None,
        created_at=datetime.now(),
        updated_at=None,
    )


def _setup_mock_uow(mock_uow_class, user_repo=None, employee_repo=None):
    """Helper to wire up a mocked AssignEmployeeUnitOfWork."""
    mock_uow = MagicMock()
    mock_uow.user_repo = user_repo or MagicMock()
    mock_uow.employee_repo = employee_repo or MagicMock()
    mock_uow.__enter__ = MagicMock(return_value=mock_uow)
    mock_uow.__exit__ = MagicMock(return_value=False)
    mock_uow_class.return_value = mock_uow
    return mock_uow


class TestBatchImportEmployees:
    """測試 EmployeeService.batch_import_employees"""

    @patch("app.services.EmployeeService.pwd_context")
    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_new_user_success(self, mock_uow_class, mock_pwd):
        """測試匯入時自動建立新使用者帳號並指派為員工"""
        mock_pwd.hash.return_value = "hashed_password"

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.add.return_value = _make_employee_model()

        _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row()])

        assert result.total == 1
        assert result.success_count == 1
        assert result.failure_count == 0
        assert len(result.new_user_credentials) == 1
        assert result.new_user_credentials[0][0] == 'john@example.com'
        assert result.new_user_credentials[0][1] == 'john'
        mock_user_repo.add.assert_called_once()
        mock_user_repo.update_role.assert_called_once()
        mock_employee_repo.add.assert_called_once()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_existing_user_success(self, mock_uow_class):
        """測試匯入時使用已存在的使用者（透過 uid 找到）"""
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = _make_user_model()
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.exists_by_user_id.return_value = False
        mock_employee_repo.add.return_value = _make_employee_model()

        _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row()])

        assert result.success_count == 1
        assert len(result.new_user_credentials) == 0  # No new user created
        mock_user_repo.add.assert_not_called()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_existing_user_by_email(self, mock_uow_class):
        """測試匯入時透過 email 找到已存在的使用者"""
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = None
        mock_user_repo.get_by_email.return_value = _make_user_model()
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.exists_by_user_id.return_value = False
        mock_employee_repo.add.return_value = _make_employee_model()

        _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row()])

        assert result.success_count == 1
        assert len(result.new_user_credentials) == 0
        mock_user_repo.get_by_email.assert_called_once_with('john@example.com')

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_duplicate_idno_skipped(self, mock_uow_class):
        """測試員工編號已存在時跳過該行"""
        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = True

        mock_uow = _setup_mock_uow(mock_uow_class, employee_repo=mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row()])

        assert result.failure_count == 1
        assert 'already exists' in result.results[0].message
        mock_uow.commit.assert_not_called()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_already_employee_skipped(self, mock_uow_class):
        """測試使用者已是員工時跳過該行"""
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = _make_user_model()

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.exists_by_user_id.return_value = True

        mock_uow = _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row()])

        assert result.failure_count == 1
        assert 'already assigned' in result.results[0].message
        mock_uow.commit.assert_not_called()

    @patch("app.services.EmployeeService.pwd_context")
    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_with_role_assignment(self, mock_uow_class, mock_pwd):
        """測試匯入時指定角色"""
        mock_pwd.hash.return_value = "hashed"

        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.name = "Developer"
        mock_role.level = 3
        mock_auth = MagicMock()
        mock_auth.name = "READ"
        mock_role.authorities = [mock_auth]

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.get_role_by_id.return_value = mock_role
        mock_employee_repo.add.return_value = _make_employee_model()

        _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        service = EmployeeService()
        result = service.batch_import_employees([_make_valid_row(role_id='1')])

        assert result.success_count == 1
        mock_employee_repo.get_role_by_id.assert_called_once_with(1)

    @patch("app.services.EmployeeService.pwd_context")
    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_import_mixed_batch(self, mock_uow_class, mock_pwd):
        """測試混合批次：一筆成功、一筆驗證失敗、一筆重複 idno"""
        mock_pwd.hash.return_value = "hashed"

        # First call: success (new user)
        # Second call: duplicate idno
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_uid.return_value = None
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_idno.side_effect = [False, True]
        mock_employee_repo.add.return_value = _make_employee_model()

        _setup_mock_uow(mock_uow_class, mock_user_repo, mock_employee_repo)

        rows = [
            _make_valid_row(idno='EMP001'),                              # success
            _make_valid_row(idno='', department='IT'),                    # validation error
            _make_valid_row(idno='EMP003', email='a@b.com', uid='aaa'),  # duplicate idno
        ]

        service = EmployeeService()
        result = service.batch_import_employees(rows)

        assert result.total == 3
        assert result.success_count == 1
        assert result.failure_count == 2
        assert result.results[0].success is True
        assert result.results[1].success is False  # validation error
        assert result.results[2].success is False  # duplicate idno

    def test_import_invalid_row_skipped(self):
        """測試無效資料列（缺少欄位）被跳過，不影響後續處理"""
        service = EmployeeService()
        rows = [
            {'idno': '', 'department': '', 'email': '', 'uid': '', 'role_id': ''},
        ]
        result = service.batch_import_employees(rows)

        assert result.total == 1
        assert result.failure_count == 1
        assert 'required' in result.results[0].message

    def test_import_empty_rows(self):
        """測試空列表回傳空結果"""
        service = EmployeeService()
        result = service.batch_import_employees([])

        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0
        assert len(result.new_user_credentials) == 0

"""
Unit tests for EmployeeService.assign_user_as_employee.
"""
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.EmployeeService import EmployeeService
from app.domain.UserModel import UserModel, UserRole, Profile as DomainProfile
from app.domain.EmployeeModel import EmployeeModel, Department
from app.exceptions.UserException import UserNotFoundError
from app.exceptions.EmployeeException import EmployeeAlreadyAssignedError, EmployeeIdnoAlreadyExistsError


# --- Test Data ---
TEST_USER_ID = str(uuid4())
TEST_IDNO = "EMP001"
TEST_DEPARTMENT = Department.IT


def _make_user_model(user_id=None, role=UserRole.NORMAL) -> UserModel:
    return UserModel.reconstitute(
        id=user_id or TEST_USER_ID,
        uid="testuser",
        email="test@example.com",
        hashed_password="hashed",
        profile=DomainProfile(name="Test", birthdate=None, description=None),
        role=role
    )


def _make_employee_model(user_id=None) -> EmployeeModel:
    return EmployeeModel(
        id=1,
        idno=TEST_IDNO,
        department=TEST_DEPARTMENT,
        user_id=user_id or TEST_USER_ID,
        role=None,
        created_at=datetime.now(),
        updated_at=None
    )


class TestAssignUserAsEmployee:
    """測試 EmployeeService.assign_user_as_employee"""

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_assign_success(self, mock_uow_class):
        """測試成功將使用者指派為員工"""
        # Arrange
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = _make_user_model()
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_user_id.return_value = False
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.add.return_value = _make_employee_model()

        mock_uow = MagicMock()
        mock_uow.user_repo = mock_user_repo
        mock_uow.employee_repo = mock_employee_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = EmployeeService()
        result = service.assign_user_as_employee(
            user_id=TEST_USER_ID,
            idno=TEST_IDNO,
            department=TEST_DEPARTMENT,
        )

        # Assert
        assert result.idno == TEST_IDNO
        assert result.user_id == TEST_USER_ID
        mock_user_repo.get_by_id.assert_called_once_with(TEST_USER_ID)
        mock_employee_repo.exists_by_user_id.assert_called_once_with(TEST_USER_ID)
        mock_employee_repo.exists_by_idno.assert_called_once_with(TEST_IDNO)
        mock_employee_repo.add.assert_called_once()
        mock_user_repo.update_role.assert_called_once_with(TEST_USER_ID, UserRole.EMPLOYEE)
        mock_uow.commit.assert_called_once()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_assign_with_role(self, mock_uow_class):
        """測試指派員工時同時指定角色"""
        # Arrange
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.name = "Developer"
        mock_role.level = 3
        mock_auth = MagicMock()
        mock_auth.name = "READ"
        mock_role.authorities = [mock_auth]

        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = _make_user_model()
        mock_user_repo.update_role.return_value = True

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_user_id.return_value = False
        mock_employee_repo.exists_by_idno.return_value = False
        mock_employee_repo.get_role_by_id.return_value = mock_role
        mock_employee_repo.add.return_value = _make_employee_model()

        mock_uow = MagicMock()
        mock_uow.user_repo = mock_user_repo
        mock_uow.employee_repo = mock_employee_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act
        service = EmployeeService()
        service.assign_user_as_employee(
            user_id=TEST_USER_ID,
            idno=TEST_IDNO,
            department=TEST_DEPARTMENT,
            role_id=1,
        )

        # Assert
        mock_employee_repo.get_role_by_id.assert_called_once_with(1)
        mock_employee_repo.add.assert_called_once()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_assign_user_not_found(self, mock_uow_class):
        """測試使用者不存在時拋出 UserNotFoundError"""
        # Arrange
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = None

        mock_uow = MagicMock()
        mock_uow.user_repo = mock_user_repo
        mock_uow.employee_repo = MagicMock()
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = EmployeeService()
        with pytest.raises(UserNotFoundError):
            service.assign_user_as_employee(
                user_id=str(uuid4()),
                idno=TEST_IDNO,
                department=TEST_DEPARTMENT,
            )
        mock_uow.commit.assert_not_called()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_assign_user_already_employee(self, mock_uow_class):
        """測試使用者已是員工時拋出 EmployeeAlreadyAssignedError"""
        # Arrange
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = _make_user_model()

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_user_id.return_value = True

        mock_uow = MagicMock()
        mock_uow.user_repo = mock_user_repo
        mock_uow.employee_repo = mock_employee_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = EmployeeService()
        with pytest.raises(EmployeeAlreadyAssignedError):
            service.assign_user_as_employee(
                user_id=TEST_USER_ID,
                idno=TEST_IDNO,
                department=TEST_DEPARTMENT,
            )
        mock_uow.commit.assert_not_called()

    @patch("app.services.EmployeeService.AssignEmployeeUnitOfWork")
    def test_assign_idno_already_exists(self, mock_uow_class):
        """測試員工編號已存在時拋出 EmployeeIdnoAlreadyExistsError"""
        # Arrange
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = _make_user_model()

        mock_employee_repo = MagicMock()
        mock_employee_repo.exists_by_user_id.return_value = False
        mock_employee_repo.exists_by_idno.return_value = True

        mock_uow = MagicMock()
        mock_uow.user_repo = mock_user_repo
        mock_uow.employee_repo = mock_employee_repo
        mock_uow.__enter__ = MagicMock(return_value=mock_uow)
        mock_uow.__exit__ = MagicMock(return_value=False)
        mock_uow_class.return_value = mock_uow

        # Act & Assert
        service = EmployeeService()
        with pytest.raises(EmployeeIdnoAlreadyExistsError):
            service.assign_user_as_employee(
                user_id=TEST_USER_ID,
                idno=TEST_IDNO,
                department=TEST_DEPARTMENT,
            )
        mock_uow.commit.assert_not_called()

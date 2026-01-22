"""
Unit tests for EmployeeRepository.
Tests the data access layer for Employee aggregates.
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.sqlalchemy.EmployeeRepository import EmployeeRepository, EmployeeQueryRepository
from app.domain.EmployeeModel import EmployeeModel, Department, RoleInfo


class TestEmployeeRepository:
    """Test suite for EmployeeRepository CRUD operations."""

    def test_add_employee_without_role(self, test_db_session: Session):
        """Test adding a new employee without a role."""
        repo = EmployeeRepository(test_db_session)

        # Create employee using domain factory
        employee = EmployeeModel.create(idno="EMP001", department=Department.IT)

        # Add to repository
        created_employee = repo.add(employee)

        # Verify
        assert created_employee.id is not None
        assert created_employee.idno == "EMP001"
        assert created_employee.department == Department.IT
        assert created_employee.role is None
        assert created_employee.created_at is not None

    def test_add_employee_with_role(self, test_db_session: Session, roles_with_authorities):
        """Test adding a new employee with a role."""
        repo = EmployeeRepository(test_db_session)

        # Create employee with role
        employee = EmployeeModel.create(idno="EMP002", department=Department.RD)
        developer_role = roles_with_authorities["developer"]

        employee.assign_role(
            role_id=developer_role.id,
            role_name=developer_role.name,
            role_level=developer_role.level,
            authorities=["READ", "WRITE"]
        )

        # Add to repository
        created_employee = repo.add(employee)

        # Verify
        assert created_employee.id is not None
        assert created_employee.idno == "EMP002"
        assert created_employee.department == Department.RD
        assert created_employee.role is not None
        assert created_employee.role.name == "Developer"
        assert created_employee.role.level == 3
        assert "READ" in created_employee.role.authorities
        assert "WRITE" in created_employee.role.authorities

    def test_get_by_id_existing(self, test_db_session: Session, roles_with_authorities):
        """Test retrieving an employee by ID."""
        repo = EmployeeRepository(test_db_session)

        # Create and add employee
        employee = EmployeeModel.create(idno="EMP003", department=Department.HR)
        created = repo.add(employee)

        # Retrieve by ID
        retrieved = repo.get_by_id(created.id)

        # Verify
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.idno == "EMP003"
        assert retrieved.department == Department.HR

    def test_get_by_id_non_existing(self, test_db_session: Session):
        """Test retrieving a non-existing employee by ID."""
        repo = EmployeeRepository(test_db_session)

        # Try to retrieve non-existing employee
        retrieved = repo.get_by_id(999)

        # Verify
        assert retrieved is None

    def test_get_by_idno_existing(self, test_db_session: Session):
        """Test retrieving an employee by idno."""
        repo = EmployeeRepository(test_db_session)

        # Create and add employee
        employee = EmployeeModel.create(idno="EMP004", department=Department.PR)
        repo.add(employee)

        # Retrieve by idno
        retrieved = repo.get_by_idno("EMP004")

        # Verify
        assert retrieved is not None
        assert retrieved.idno == "EMP004"
        assert retrieved.department == Department.PR

    def test_get_by_idno_non_existing(self, test_db_session: Session):
        """Test retrieving a non-existing employee by idno."""
        repo = EmployeeRepository(test_db_session)

        # Try to retrieve non-existing employee
        retrieved = repo.get_by_idno("NONEXIST")

        # Verify
        assert retrieved is None

    def test_get_all_empty(self, test_db_session: Session):
        """Test retrieving all employees when none exist."""
        repo = EmployeeRepository(test_db_session)

        # Get all
        employees = repo.get_all()

        # Verify
        assert employees == []

    def test_get_all_multiple(self, test_db_session: Session):
        """Test retrieving all employees."""
        repo = EmployeeRepository(test_db_session)

        # Create multiple employees
        employees = [
            EmployeeModel.create(idno="EMP005", department=Department.IT),
            EmployeeModel.create(idno="EMP006", department=Department.HR),
            EmployeeModel.create(idno="EMP007", department=Department.RD),
        ]

        for emp in employees:
            repo.add(emp)

        # Get all
        all_employees = repo.get_all()

        # Verify
        assert len(all_employees) == 3
        idnos = [emp.idno for emp in all_employees]
        assert "EMP005" in idnos
        assert "EMP006" in idnos
        assert "EMP007" in idnos

    def test_get_by_department(self, test_db_session: Session):
        """Test retrieving employees by department."""
        repo = EmployeeRepository(test_db_session)

        # Create employees in different departments
        repo.add(EmployeeModel.create(idno="EMP008", department=Department.IT))
        repo.add(EmployeeModel.create(idno="EMP009", department=Department.IT))
        repo.add(EmployeeModel.create(idno="EMP010", department=Department.HR))

        # Get IT employees
        it_employees = repo.get_by_department(Department.IT)

        # Verify
        assert len(it_employees) == 2
        for emp in it_employees:
            assert emp.department == Department.IT

    def test_update_employee_department(self, test_db_session: Session):
        """Test updating an employee's department."""
        repo = EmployeeRepository(test_db_session)

        # Create employee
        employee = EmployeeModel.create(idno="EMP011", department=Department.IT)
        created = repo.add(employee)

        # Change department
        created.change_department(Department.HR)

        # Update
        updated = repo.update(created)

        # Verify
        assert updated.department == Department.HR
        assert updated.updated_at is not None

    def test_update_employee_role(self, test_db_session: Session, roles_with_authorities):
        """Test updating an employee's role."""
        repo = EmployeeRepository(test_db_session)

        # Create employee without role
        employee = EmployeeModel.create(idno="EMP012", department=Department.RD)
        created = repo.add(employee)

        # Assign role
        manager_role = roles_with_authorities["manager"]
        created.assign_role(
            role_id=manager_role.id,
            role_name=manager_role.name,
            role_level=manager_role.level,
            authorities=["READ", "WRITE", "DELETE", "ADMIN"]
        )

        # Update
        updated = repo.update(created)

        # Verify
        assert updated.role is not None
        assert updated.role.name == "Manager"
        assert updated.role.level == 5
        assert len(updated.role.authorities) == 4

    def test_update_non_existing_employee(self, test_db_session: Session):
        """Test updating a non-existing employee raises error."""
        repo = EmployeeRepository(test_db_session)

        # Create employee with fake ID
        employee = EmployeeModel(
            id=999,
            idno="FAKE",
            department=Department.IT,
            created_at=datetime.now()
        )

        # Try to update
        with pytest.raises(ValueError, match="Employee with id 999 not found"):
            repo.update(employee)

    def test_delete_existing_employee(self, test_db_session: Session):
        """Test deleting an existing employee."""
        repo = EmployeeRepository(test_db_session)

        # Create employee
        employee = EmployeeModel.create(idno="EMP013", department=Department.BD)
        created = repo.add(employee)

        # Delete
        result = repo.delete(created.id)

        # Verify
        assert result is True
        assert repo.get_by_id(created.id) is None

    def test_delete_non_existing_employee(self, test_db_session: Session):
        """Test deleting a non-existing employee."""
        repo = EmployeeRepository(test_db_session)

        # Try to delete non-existing employee
        result = repo.delete(999)

        # Verify
        assert result is False

    def test_exists_by_idno_true(self, test_db_session: Session):
        """Test checking if employee exists by idno."""
        repo = EmployeeRepository(test_db_session)

        # Create employee
        repo.add(EmployeeModel.create(idno="EMP014", department=Department.IT))

        # Check existence
        exists = repo.exists_by_idno("EMP014")

        # Verify
        assert exists is True

    def test_exists_by_idno_false(self, test_db_session: Session):
        """Test checking if non-existing employee exists by idno."""
        repo = EmployeeRepository(test_db_session)

        # Check existence
        exists = repo.exists_by_idno("NONEXIST")

        # Verify
        assert exists is False

    def test_domain_model_preserves_role_authorities(self, test_db_session: Session, roles_with_authorities):
        """Test that converting to domain model preserves all role authorities."""
        repo = EmployeeRepository(test_db_session)

        # Create employee with developer role
        employee = EmployeeModel.create(idno="EMP015", department=Department.IT)
        developer_role = roles_with_authorities["developer"]

        employee.assign_role(
            role_id=developer_role.id,
            role_name=developer_role.name,
            role_level=developer_role.level,
            authorities=[auth.name for auth in developer_role.authorities]
        )

        # Add and retrieve
        created = repo.add(employee)
        retrieved = repo.get_by_id(created.id)

        # Verify authorities are preserved
        assert retrieved.role is not None
        assert len(retrieved.role.authorities) == 2
        assert set(retrieved.role.authorities) == {"READ", "WRITE"}


class TestEmployeeQueryRepository:
    """Test suite for EmployeeQueryRepository specialized queries."""

    def test_get_employees_with_authority(self, test_db_session: Session, roles_with_authorities):
        """Test getting employees with a specific authority."""
        repo = EmployeeRepository(test_db_session)
        query_repo = EmployeeQueryRepository(test_db_session)

        # Create employees with different roles
        manager_role = roles_with_authorities["manager"]
        developer_role = roles_with_authorities["developer"]
        intern_role = roles_with_authorities["intern"]

        emp1 = EmployeeModel.create(idno="EMP016", department=Department.IT)
        emp1.assign_role(
            role_id=manager_role.id,
            role_name=manager_role.name,
            role_level=manager_role.level,
            authorities=[auth.name for auth in manager_role.authorities]
        )

        emp2 = EmployeeModel.create(idno="EMP017", department=Department.RD)
        emp2.assign_role(
            role_id=developer_role.id,
            role_name=developer_role.name,
            role_level=developer_role.level,
            authorities=[auth.name for auth in developer_role.authorities]
        )

        emp3 = EmployeeModel.create(idno="EMP018", department=Department.HR)
        emp3.assign_role(
            role_id=intern_role.id,
            role_name=intern_role.name,
            role_level=intern_role.level,
            authorities=[auth.name for auth in intern_role.authorities]
        )

        repo.add(emp1)
        repo.add(emp2)
        repo.add(emp3)

        # Query employees with WRITE authority
        employees_with_write = query_repo.get_employees_with_authority("WRITE")

        # Verify (Manager and Developer have WRITE, Intern does not)
        assert len(employees_with_write) == 2
        idnos = [emp.idno for emp in employees_with_write]
        assert "EMP016" in idnos  # Manager
        assert "EMP017" in idnos  # Developer
        assert "EMP018" not in idnos  # Intern

    def test_get_employees_with_authority_none_found(self, test_db_session: Session):
        """Test getting employees with an authority when none exist."""
        query_repo = EmployeeQueryRepository(test_db_session)

        # Query with no employees
        employees = query_repo.get_employees_with_authority("ADMIN")

        # Verify
        assert employees == []

    def test_get_employees_with_admin_authority(self, test_db_session: Session, roles_with_authorities):
        """Test getting employees with ADMIN authority."""
        repo = EmployeeRepository(test_db_session)
        query_repo = EmployeeQueryRepository(test_db_session)

        # Create manager with ADMIN authority
        manager_role = roles_with_authorities["manager"]
        emp = EmployeeModel.create(idno="EMP019", department=Department.IT)
        emp.assign_role(
            role_id=manager_role.id,
            role_name=manager_role.name,
            role_level=manager_role.level,
            authorities=[auth.name for auth in manager_role.authorities]
        )
        repo.add(emp)

        # Query
        admins = query_repo.get_employees_with_authority("ADMIN")

        # Verify
        assert len(admins) == 1
        assert admins[0].idno == "EMP019"
        assert admins[0].has_authority("ADMIN")

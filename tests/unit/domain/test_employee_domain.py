import pytest
from datetime import datetime
from app.domain.EmployeeModel import EmployeeModel, Department, RoleInfo


# --- Test Data ---
TEST_IDNO = "EMP001"
TEST_DEPARTMENT = Department.IT
TEST_ROLE_ID = 1
TEST_ROLE_NAME = "Senior Developer"
TEST_ROLE_LEVEL = 5
TEST_AUTHORITIES = ["USER_READ", "USER_WRITE", "PROJECT_READ"]


def test_employee_creation_with_valid_data():
    """
    測試使用有效資料建立員工實體。
    """
    employee = EmployeeModel.create(
        idno=TEST_IDNO,
        department=TEST_DEPARTMENT
    )

    # 斷言物件型別正確
    assert isinstance(employee, EmployeeModel)

    # 斷言屬性符合預期
    assert employee.id is None  # ID should be None before persistence
    assert employee.idno == TEST_IDNO
    assert employee.department == TEST_DEPARTMENT
    assert employee.role is None
    assert isinstance(employee.created_at, datetime)
    assert employee.updated_at is None


def test_employee_creation_with_string_department():
    """
    測試使用字串形式的部門建立員工。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department="hr")

    assert employee.department == Department.HR


def test_employee_creation_with_uppercase_string_department():
    """
    測試使用大寫字串形式的部門建立員工。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department="RD")

    assert employee.department == Department.RD


def test_employee_creation_with_empty_idno_raises_error():
    """
    測試使用空白員工編號建立員工時會拋出 ValueError。
    """
    with pytest.raises(ValueError, match="Employee ID number cannot be empty"):
        EmployeeModel.create(idno="", department=TEST_DEPARTMENT)

    with pytest.raises(ValueError, match="Employee ID number cannot be empty"):
        EmployeeModel.create(idno="   ", department=TEST_DEPARTMENT)


def test_employee_creation_with_invalid_department_raises_error():
    """
    測試使用無效的部門名稱建立員工時會拋出 ValueError。
    """
    with pytest.raises(ValueError, match="Invalid department"):
        EmployeeModel.create(idno=TEST_IDNO, department="INVALID_DEPT")


def test_employee_idno_is_stripped():
    """
    測試員工編號會自動去除前後空白。
    """
    employee = EmployeeModel.create(idno="  EMP002  ", department=TEST_DEPARTMENT)

    assert employee.idno == "EMP002"


def test_employee_assign_role():
    """
    測試分配角色給員工。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)

    employee.assign_role(
        role_id=TEST_ROLE_ID,
        role_name=TEST_ROLE_NAME,
        role_level=TEST_ROLE_LEVEL,
        authorities=TEST_AUTHORITIES
    )

    # 斷言角色已正確分配
    assert employee.role is not None
    assert isinstance(employee.role, RoleInfo)
    assert employee.role.id == TEST_ROLE_ID
    assert employee.role.name == TEST_ROLE_NAME
    assert employee.role.level == TEST_ROLE_LEVEL
    assert employee.role.authorities == TEST_AUTHORITIES

    # 斷言 updated_at 已被設定
    assert employee.updated_at is not None
    assert isinstance(employee.updated_at, datetime)


def test_employee_change_department_with_enum():
    """
    測試使用枚舉類型變更員工部門。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)
    original_updated_at = employee.updated_at

    employee.change_department(Department.HR)

    assert employee.department == Department.HR
    assert employee.updated_at != original_updated_at
    assert isinstance(employee.updated_at, datetime)


def test_employee_change_department_with_string():
    """
    測試使用字串變更員工部門。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)

    employee.change_department("bd")

    assert employee.department == Department.BD


def test_employee_change_department_with_invalid_string_raises_error():
    """
    測試使用無效的部門字串變更部門時會拋出 ValueError。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)

    with pytest.raises(ValueError, match="Invalid department"):
        employee.change_department("INVALID")


def test_employee_has_authority_returns_true_when_authority_exists():
    """
    測試員工擁有特定權限時 has_authority 返回 True。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)
    employee.assign_role(
        role_id=TEST_ROLE_ID,
        role_name=TEST_ROLE_NAME,
        role_level=TEST_ROLE_LEVEL,
        authorities=TEST_AUTHORITIES
    )

    assert employee.has_authority("USER_READ") is True
    assert employee.has_authority("USER_WRITE") is True
    assert employee.has_authority("PROJECT_READ") is True


def test_employee_has_authority_returns_false_when_authority_not_exists():
    """
    測試員工沒有特定權限時 has_authority 返回 False。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)
    employee.assign_role(
        role_id=TEST_ROLE_ID,
        role_name=TEST_ROLE_NAME,
        role_level=TEST_ROLE_LEVEL,
        authorities=TEST_AUTHORITIES
    )

    assert employee.has_authority("ADMIN_ACCESS") is False


def test_employee_has_authority_returns_false_when_no_role():
    """
    測試員工沒有角色時 has_authority 返回 False。
    """
    employee = EmployeeModel.create(idno=TEST_IDNO, department=TEST_DEPARTMENT)

    assert employee.has_authority("USER_READ") is False


def test_employee_equality_by_idno():
    """
    測試員工實體的相等性判斷（基於員工編號）。
    """
    employee1 = EmployeeModel.create(idno=TEST_IDNO, department=Department.IT)
    employee2 = EmployeeModel.create(idno=TEST_IDNO, department=Department.HR)
    employee3 = EmployeeModel.create(idno="EMP002", department=Department.IT)

    # 相同員工編號的員工應該相等（即使部門不同）
    assert employee1 == employee2

    # 不同員工編號的員工應該不相等
    assert employee1 != employee3


def test_employee_hash_consistency():
    """
    測試員工實體的雜湊值一致性。
    """
    employee1 = EmployeeModel.create(idno=TEST_IDNO, department=Department.IT)
    employee2 = EmployeeModel.create(idno=TEST_IDNO, department=Department.HR)

    # 相同員工編號的員工應該有相同的雜湊值
    assert hash(employee1) == hash(employee2)


def test_employee_can_be_used_in_set():
    """
    測試員工實體可以用於集合操作。
    """
    employee1 = EmployeeModel.create(idno="EMP001", department=Department.IT)
    employee2 = EmployeeModel.create(idno="EMP001", department=Department.HR)  # Duplicate
    employee3 = EmployeeModel.create(idno="EMP002", department=Department.IT)

    employee_set = {employee1, employee2, employee3}

    # 集合應該只包含兩個唯一的員工
    assert len(employee_set) == 2


def test_employee_with_id():
    """
    測試手動建立包含 ID 的員工實體（模擬從資料庫讀取）。
    """
    now = datetime.now()
    employee = EmployeeModel(
        id=1,
        idno=TEST_IDNO,
        department=TEST_DEPARTMENT,
        role=None,
        created_at=now,
        updated_at=None
    )

    assert employee.id == 1
    assert employee.idno == TEST_IDNO
    assert employee.department == TEST_DEPARTMENT
    assert employee.created_at == now


def test_department_enum_values():
    """
    測試 Department 枚舉包含所有預期的部門。
    """
    assert Department.HR.value == 'HR'
    assert Department.IT.value == 'IT'
    assert Department.PR.value == 'PR'
    assert Department.RD.value == 'RD'
    assert Department.BD.value == 'BD'


def test_employee_creation_with_user_id():
    """測試使用 user_id 建立員工"""
    employee = EmployeeModel.create(
        idno="EMP020",
        department=Department.IT,
        user_id="some-uuid-string"
    )
    assert employee.user_id == "some-uuid-string"


def test_employee_creation_without_user_id():
    """測試不帶 user_id 建立員工，預設為 None"""
    employee = EmployeeModel.create(idno="EMP021", department=Department.IT)
    assert employee.user_id is None


def test_role_info_value_object():
    """
    測試 RoleInfo 值物件的建立。
    """
    role_info = RoleInfo(
        id=TEST_ROLE_ID,
        name=TEST_ROLE_NAME,
        level=TEST_ROLE_LEVEL,
        authorities=TEST_AUTHORITIES
    )

    assert role_info.id == TEST_ROLE_ID
    assert role_info.name == TEST_ROLE_NAME
    assert role_info.level == TEST_ROLE_LEVEL
    assert role_info.authorities == TEST_AUTHORITIES

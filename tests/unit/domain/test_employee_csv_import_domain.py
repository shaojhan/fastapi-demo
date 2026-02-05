import pytest
from app.domain.EmployeeCsvImportModel import EmployeeCsvRow, RowResult, CsvImportResult
from app.domain.EmployeeModel import Department


# --- Test Data ---
VALID_ROW = {
    'idno': 'EMP001',
    'department': 'IT',
    'email': 'john@example.com',
    'uid': 'john',
    'role_id': '1',
}


class TestEmployeeCsvRow:
    """測試 EmployeeCsvRow 值物件"""

    def test_from_dict_valid_data(self):
        """測試使用完整有效資料建立 EmployeeCsvRow"""
        row = EmployeeCsvRow.from_dict(VALID_ROW)

        assert row.idno == 'EMP001'
        assert row.department == Department.IT
        assert row.email == 'john@example.com'
        assert row.uid == 'john'
        assert row.role_id == 1

    def test_from_dict_case_insensitive_department(self):
        """測試部門字串不區分大小寫"""
        row = EmployeeCsvRow.from_dict({**VALID_ROW, 'department': 'hr'})
        assert row.department == Department.HR

        row2 = EmployeeCsvRow.from_dict({**VALID_ROW, 'department': 'Rd'})
        assert row2.department == Department.RD

    def test_from_dict_strips_whitespace(self):
        """測試所有欄位會自動去除前後空白"""
        row = EmployeeCsvRow.from_dict({
            'idno': '  EMP002  ',
            'department': '  IT  ',
            'email': '  test@mail.com  ',
            'uid': '  testuser  ',
            'role_id': '  2  ',
        })

        assert row.idno == 'EMP002'
        assert row.email == 'test@mail.com'
        assert row.uid == 'testuser'
        assert row.role_id == 2

    def test_from_dict_optional_role_id_empty(self):
        """測試 role_id 為空字串時設為 None"""
        row = EmployeeCsvRow.from_dict({**VALID_ROW, 'role_id': ''})
        assert row.role_id is None

    def test_from_dict_optional_role_id_none(self):
        """測試 role_id 為 None 時設為 None"""
        row = EmployeeCsvRow.from_dict({**VALID_ROW, 'role_id': None})
        assert row.role_id is None

    def test_from_dict_optional_role_id_present(self):
        """測試 role_id 為有效數字字串時正確轉換"""
        row = EmployeeCsvRow.from_dict({**VALID_ROW, 'role_id': '5'})
        assert row.role_id == 5

    def test_from_dict_missing_idno_raises(self):
        """測試缺少 idno 時拋出 ValueError"""
        with pytest.raises(ValueError, match='idno is required'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'idno': ''})

    def test_from_dict_missing_department_raises(self):
        """測試缺少 department 時拋出 ValueError"""
        with pytest.raises(ValueError, match='department is required'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'department': ''})

    def test_from_dict_missing_email_raises(self):
        """測試缺少 email 時拋出 ValueError"""
        with pytest.raises(ValueError, match='email is required'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'email': ''})

    def test_from_dict_missing_uid_raises(self):
        """測試缺少 uid 時拋出 ValueError"""
        with pytest.raises(ValueError, match='uid is required'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'uid': ''})

    def test_from_dict_invalid_department_raises(self):
        """測試無效部門名稱時拋出 ValueError"""
        with pytest.raises(ValueError, match='Invalid department'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'department': 'INVALID'})

    def test_from_dict_invalid_role_id_raises(self):
        """測試無效 role_id 時拋出 ValueError"""
        with pytest.raises(ValueError, match='Invalid role_id'):
            EmployeeCsvRow.from_dict({**VALID_ROW, 'role_id': 'abc'})

    def test_frozen_immutability(self):
        """測試 EmployeeCsvRow 為不可變物件"""
        row = EmployeeCsvRow.from_dict(VALID_ROW)
        with pytest.raises(AttributeError):
            row.idno = 'EMP999'


class TestRowResult:
    """測試 RowResult"""

    def test_ok_factory(self):
        """測試 ok 工廠方法建立成功結果"""
        result = RowResult.ok(row=1, idno='EMP001')

        assert result.row == 1
        assert result.idno == 'EMP001'
        assert result.success is True
        assert result.message == 'OK'

    def test_fail_factory(self):
        """測試 fail 工廠方法建立失敗結果"""
        result = RowResult.fail(row=2, idno='EMP002', message='Duplicate idno')

        assert result.row == 2
        assert result.idno == 'EMP002'
        assert result.success is False
        assert result.message == 'Duplicate idno'


class TestCsvImportResult:
    """測試 CsvImportResult"""

    def test_empty_result_counts(self):
        """測試空結果的計數"""
        result = CsvImportResult()

        assert result.total == 0
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_mixed_results_counts(self):
        """測試混合成功與失敗結果的計數"""
        result = CsvImportResult()
        result.results.append(RowResult.ok(row=1, idno='EMP001'))
        result.results.append(RowResult.ok(row=2, idno='EMP002'))
        result.results.append(RowResult.fail(row=3, idno='EMP003', message='error'))

        assert result.total == 3
        assert result.success_count == 2
        assert result.failure_count == 1

    def test_new_user_credentials_tracking(self):
        """測試新建使用者的帳密追蹤"""
        result = CsvImportResult()
        result.new_user_credentials.append(('a@mail.com', 'user_a', 'pass123'))
        result.new_user_credentials.append(('b@mail.com', 'user_b', 'pass456'))

        assert len(result.new_user_credentials) == 2
        assert result.new_user_credentials[0] == ('a@mail.com', 'user_a', 'pass123')

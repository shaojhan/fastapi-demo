# 領域模型單元測試

本目錄包含領域模型的單元測試。

## 測試文件

### test_authority_domain.py
測試 `AuthorityModel` 領域模型的所有功能。

**測試覆蓋範圍：** 95%

**測試項目：**
- ✅ 建立權限實體（有描述和無描述）
- ✅ 權限名稱自動轉換為大寫
- ✅ 權限名稱自動去除空白
- ✅ 空白名稱驗證（拋出 ValueError）
- ✅ 更新權限描述
- ✅ 權限相等性判斷（基於名稱）
- ✅ 權限雜湊值一致性
- ✅ 權限可用於集合操作（set）
- ✅ 從資料庫讀取權限（包含 ID）

### test_employee_domain.py
測試 `EmployeeModel` 領域模型的所有功能。

**測試覆蓋範圍：** 98%

**測試項目：**
- ✅ 建立員工實體（使用枚舉和字串形式的部門）
- ✅ 員工編號自動去除空白
- ✅ 空白員工編號驗證（拋出 ValueError）
- ✅ 無效部門名稱驗證（拋出 ValueError）
- ✅ 分配角色給員工
- ✅ 變更員工部門（使用枚舉和字串）
- ✅ 檢查員工是否擁有特定權限
- ✅ 無角色時的權限檢查
- ✅ 員工相等性判斷（基於員工編號）
- ✅ 員工雜湊值一致性
- ✅ 員工可用於集合操作（set）
- ✅ 從資料庫讀取員工（包含 ID）
- ✅ Department 枚舉值驗證
- ✅ RoleInfo 值物件建立

## 執行測試

執行所有領域模型測試：
```bash
poetry run pytest tests/unit/domain/ -v
```

執行特定測試文件：
```bash
poetry run pytest tests/unit/domain/test_authority_domain.py -v
poetry run pytest tests/unit/domain/test_employee_domain.py -v
```

生成測試覆蓋率報告：
```bash
poetry run pytest tests/unit/domain/test_authority_domain.py tests/unit/domain/test_employee_domain.py \
  --cov=app.domain.AuthorityModel \
  --cov=app.domain.EmployeeModel \
  --cov-report=term-missing
```

## 測試結果

```
AuthorityModel: 11 tests passed (95% coverage)
EmployeeModel:  19 tests passed (98% coverage)
Total:          30 tests passed (97% coverage)
```

## 測試原則

1. **完整性**：測試所有公開方法和工廠方法
2. **邊界條件**：測試空值、無效輸入等邊界情況
3. **異常處理**：驗證適當的錯誤拋出
4. **領域邏輯**：測試領域規則和業務邏輯
5. **值物件**：驗證相等性和雜湊值的正確實現

"""
Integration tests: Employee CSV upload endpoints.

Tests the full HTTP → Router → Service → Repository → SQLite stack for:
- POST /employees/upload-csv     — synchronous batch import
- POST /employees/upload-csv-async — asynchronous batch import (publisher mocked)

Notes:
- New user creation in CSV import assigns a placeholder birthdate (profile.birthdate is NOT NULL).
- Empty CSV rows are rejected by FileReadService with HTTP 400.
- Async task dispatch is replaced by the test app's no-op background task publisher.
"""
import io
import pytest
from unittest.mock import patch, AsyncMock

from tests.integration.conftest import get_auth_token, auth_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_csv_bytes(rows: list[dict], headers: list[str] | None = None) -> bytes:
    """Build a minimal CSV byte string from a list of dicts."""
    if headers is None:
        headers = ["idno", "department", "email", "uid", "role_id"]
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines).encode("utf-8")


def _csv_file(content: bytes, filename: str = "employees.csv"):
    """Return a dict suitable for httpx multipart upload."""
    return {"file": (filename, io.BytesIO(content), "text/csv")}


# ---------------------------------------------------------------------------
# POST /employees/upload-csv — synchronous upload
# ---------------------------------------------------------------------------

class TestUploadEmployeesCsvSync:
    """測試同步 CSV 批次匯入。"""

    def test_admin_can_upload_valid_csv(self, client, seed_admin, seed_normal_user):
        """Admin 成功上傳有效 CSV（使用已存在的 user），全部成功匯入。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        rows = [{
            "idno": "CSVTEST001",
            "department": "IT",
            "email": seed_normal_user["email"],
            "uid": seed_normal_user["uid"],
            "role_id": "0",
        }]
        csv_content = _make_csv_bytes(rows)

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["success_count"] == 1
        assert body["failure_count"] == 0
        assert body["results"][0]["success"] is True
        assert body["results"][0]["idno"] == "CSVTEST001"

    def test_upload_multiple_rows(self, client, seed_admin, seed_normal_user, seed_unverified_user):
        """上傳多筆員工資料（使用已存在的 users），全部成功。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        rows = [
            {
                "idno": "MULTI001",
                "department": "IT",
                "email": seed_normal_user["email"],
                "uid": seed_normal_user["uid"],
                "role_id": "0",
            },
            {
                "idno": "MULTI002",
                "department": "HR",
                "email": seed_unverified_user["email"],
                "uid": seed_unverified_user["uid"],
                "role_id": "0",
            },
        ]
        csv_content = _make_csv_bytes(rows)

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["success_count"] == 2
        assert body["failure_count"] == 0

    def test_upload_csv_with_duplicate_idno_reports_failure(
        self, client, seed_admin, seed_normal_user, seed_unverified_user
    ):
        """重複的員工編號（第二筆失敗），回傳部分成功。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        rows = [
            {
                "idno": "DUPIDNO001",
                "department": "IT",
                "email": seed_normal_user["email"],
                "uid": seed_normal_user["uid"],
                "role_id": "0",
            },
            {
                "idno": "DUPIDNO001",  # 同 idno，應失敗
                "department": "HR",
                "email": seed_unverified_user["email"],
                "uid": seed_unverified_user["uid"],
                "role_id": "0",
            },
        ]
        csv_content = _make_csv_bytes(rows)

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["success_count"] == 1
        assert body["failure_count"] == 1

    def test_upload_csv_missing_required_columns_returns_400(self, client, seed_admin):
        """CSV 缺少必填欄位，回傳 400。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        # 缺少 idno 欄位
        csv_content = _make_csv_bytes(
            [{"department": "IT", "email": "x@test.com", "uid": "x", "role_id": "0"}],
            headers=["department", "email", "uid", "role_id"],
        )

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_upload_empty_csv_returns_400(self, client, seed_admin):
        """上傳空 CSV（只有標頭，無資料行），FileReadService 拒絕並回傳 400。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        csv_content = _make_csv_bytes([])  # no rows

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_non_admin_cannot_upload_csv(self, client, seed_normal_user):
        """一般使用者無法上傳 CSV，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        csv_content = _make_csv_bytes([{
            "idno": "X001", "department": "IT",
            "email": "x@test.com", "uid": "xuser", "role_id": "0"
        }])

        resp = client.post(
            "/employees/upload-csv",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_upload_csv(self, client):
        """未認證使用者無法上傳，回傳 401。"""
        csv_content = _make_csv_bytes([{
            "idno": "X001", "department": "IT",
            "email": "x@test.com", "uid": "xuser", "role_id": "0"
        }])
        resp = client.post("/employees/upload-csv", files=_csv_file(csv_content))
        assert resp.status_code == 401

    def test_upload_existing_user_email_assigns_employee_without_new_password(
        self, client, seed_admin, seed_normal_user
    ):
        """已存在使用者 email，匯入後指派為員工，不發送密碼 email。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        rows = [
            {
                "idno": "EXIST001",
                "department": "IT",
                "email": seed_normal_user["email"],
                "uid": seed_normal_user["uid"],
                "role_id": "0",
            }
        ]
        csv_content = _make_csv_bytes(rows)

        with patch(
            "app.services.EmailService.EmailService.send_employee_password_email",
            new_callable=AsyncMock,
        ) as mock_email:
            resp = client.post(
                "/employees/upload-csv",
                files=_csv_file(csv_content),
                headers=auth_headers(token),
            )
            # No new user created → no password email
            mock_email.assert_not_called()

        assert resp.status_code == 200
        body = resp.json()
        assert body["success_count"] == 1

    def test_upload_csv_creates_brand_new_user(self, client, seed_admin):
        """CSV 匯入全新使用者（uid/email 皆不存在），建立帳號並寄送密碼 email。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        new_email = "brandnew@test.com"
        new_uid = "brandnewuser"
        rows = [
            {
                "idno": "NEWUSER001",
                "department": "IT",
                "email": new_email,
                "uid": new_uid,
                "role_id": "0",
            }
        ]
        csv_content = _make_csv_bytes(rows)

        with patch(
            "app.services.EmailService.EmailService.send_employee_password_email",
            new_callable=AsyncMock,
        ) as mock_email:
            resp = client.post(
                "/employees/upload-csv",
                files=_csv_file(csv_content),
                headers=auth_headers(token),
            )
            # New user created → password email sent once with the new credentials
            mock_email.assert_awaited_once()
            sent_email, sent_uid, sent_password = mock_email.await_args.args[:3]
            assert sent_email == new_email
            assert sent_uid == new_uid
            assert sent_password  # a random password was generated

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["success_count"] == 1
        assert body["failure_count"] == 0
        assert body["results"][0]["success"] is True
        assert body["results"][0]["idno"] == "NEWUSER001"


# ---------------------------------------------------------------------------
# POST /employees/upload-csv-async — asynchronous upload
# ---------------------------------------------------------------------------

class TestUploadEmployeesCsvAsync:
    """測試非同步 CSV 批次匯入（background task publisher）。"""

    def test_admin_can_upload_csv_async_returns_task_id(self, client, seed_admin, seed_normal_user):
        """Admin 成功上傳並取得 task_id（task publisher 已替換為 no-op）。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        rows = [{
            "idno": "ASYNC001",
            "department": "IT",
            "email": seed_normal_user["email"],
            "uid": seed_normal_user["uid"],
            "role_id": "0",
        }]
        csv_content = _make_csv_bytes(rows)

        resp = client.post(
            "/employees/upload-csv-async",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body
        assert body["task_id"] == "noop-task-id"

    def test_async_upload_missing_columns_returns_400(self, client, seed_admin):
        """非同步上傳缺少必填欄位，回傳 400（在 task 提交前驗證）。"""
        token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        csv_content = _make_csv_bytes(
            [{"email": "x@test.com"}],
            headers=["email"],
        )

        resp = client.post(
            "/employees/upload-csv-async",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_non_admin_cannot_upload_csv_async(self, client, seed_normal_user):
        """一般使用者無法使用非同步上傳，回傳 403。"""
        token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        csv_content = _make_csv_bytes([{
            "idno": "X001", "department": "IT",
            "email": "x@test.com", "uid": "xuser", "role_id": "0"
        }])

        resp = client.post(
            "/employees/upload-csv-async",
            files=_csv_file(csv_content),
            headers=auth_headers(token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_upload_csv_async(self, client):
        """未認證使用者無法使用非同步上傳，回傳 401。"""
        csv_content = _make_csv_bytes([{
            "idno": "X001", "department": "IT",
            "email": "x@test.com", "uid": "xuser", "role_id": "0"
        }])
        resp = client.post("/employees/upload-csv-async", files=_csv_file(csv_content))
        assert resp.status_code == 401

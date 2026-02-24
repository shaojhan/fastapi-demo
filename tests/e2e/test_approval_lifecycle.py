"""
E2E 測試：審核申請完整生命週期。

涵蓋三種結果路徑：
1. 核准流程：PENDING → Admin 核准 → APPROVED
2. 取消流程：PENDING → 申請人取消 → CANCELLED
3. 拒絕流程：PENDING → Admin 拒絕 → REJECTED
4. 混合場景：同一員工同時管理多個不同狀態的申請

此測試橫跨 employee 與 approval 兩個功能模組，
驗證審核狀態機在各種操作路徑下的正確性。
"""

import pytest
from tests.e2e.conftest import get_auth_token, auth_headers


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def approval_scenario(client, seed_admin, seed_normal_user):
    """
    準備審核測試場景：
    - seed_admin 為 Admin（自動成為核准人）
    - 透過 /employees/assign API 將 seed_normal_user 指派為員工
      （approval service 會查詢 Employee 資料表，單純設定 role 不夠）
    """
    admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

    # 透過 API 指派員工，讓 Employee 資料表有對應記錄
    assign_resp = client.post(
        "/employees/assign",
        json={
            "user_id": seed_normal_user["id"],
            "idno": "EMP-ALC-001",
            "department": "IT",
            "role_id": 0,
        },
        headers=auth_headers(admin_token),
    )
    assert assign_resp.status_code == 200, f"Employee assign failed: {assign_resp.text}"

    return {
        "admin": seed_admin,
        "employee": seed_normal_user,
        "admin_token": admin_token,
    }


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

_ANNUAL_LEAVE = {
    "leave_type": "ANNUAL",
    "start_date": "2026-05-01T09:00:00",
    "end_date": "2026-05-05T18:00:00",
    "reason": "年假旅遊",
}

_SICK_LEAVE = {
    "leave_type": "SICK",
    "start_date": "2026-05-10T09:00:00",
    "end_date": "2026-05-10T18:00:00",
    "reason": "身體不適需就醫",
}

_EXPENSE = {
    "amount": 2500.0,
    "category": "差旅費",
    "description": "出差住宿費用",
    "receipt_url": None,
}


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestApproveFlow:
    """測試核准流程：PENDING → APPROVED。"""

    def test_leave_approval_lifecycle(self, client, approval_scenario):
        """
        完整旅程：員工提交年假 → 確認 PENDING → Admin 核准 → 確認 APPROVED。

        Step 1: 員工提交年假申請
        Step 2: 員工取得申請詳情，確認狀態為 PENDING
        Step 3: Admin 查看待核准列表，確認申請出現其中
        Step 4: Admin 核准申請
        Step 5: 員工確認狀態已變為 APPROVED
        Step 6: APPROVED 申請從 Admin 待核准列表消失
        """
        emp = approval_scenario["employee"]
        admin_token = approval_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # Step 1: 員工提交年假申請
        create_resp = client.post(
            "/approvals/leave",
            json=_ANNUAL_LEAVE,
            headers=auth_headers(emp_token),
        )
        assert create_resp.status_code == 200, f"Create leave failed: {create_resp.text}"
        create_data = create_resp.json()
        assert create_data["status"] == "PENDING"
        assert create_data["type"] == "LEAVE"
        request_id = create_data["id"]

        # Step 2: 員工取得申請詳情
        detail_resp = client.get(
            f"/approvals/{request_id}", headers=auth_headers(emp_token)
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["status"] == "PENDING"
        assert detail["type"] == "LEAVE"
        assert len(detail["steps"]) >= 1  # 簽核鏈至少一個步驟

        # Step 3: Admin 查看待核准列表
        pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert pending_resp.status_code == 200
        pending_ids = [item["id"] for item in pending_resp.json()["items"]]
        assert request_id in pending_ids

        # Step 4: Admin 核准
        approve_resp = client.post(
            f"/approvals/{request_id}/approve",
            json={"comment": "同意，假期愉快！"},
            headers=auth_headers(admin_token),
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"

        # Step 5: 員工確認 APPROVED
        final_resp = client.get(
            f"/approvals/{request_id}", headers=auth_headers(emp_token)
        )
        assert final_resp.status_code == 200
        assert final_resp.json()["status"] == "APPROVED"

        # Step 6: 申請從 Admin 待核准列表消失
        after_pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert after_pending_resp.status_code == 200
        remaining_ids = [item["id"] for item in after_pending_resp.json()["items"]]
        assert request_id not in remaining_ids


class TestCancelFlow:
    """測試取消申請流程：PENDING → CANCELLED。"""

    def test_employee_cancels_expense_request(self, client, approval_scenario):
        """
        完整旅程：員工提交費用申請 → 確認 PENDING → 員工取消 → 確認 CANCELLED。

        Step 1: 員工提交費用申請
        Step 2: 確認狀態為 PENDING
        Step 3: 員工取消申請
        Step 4: 確認狀態為 CANCELLED
        Step 5: 「我的申請」列表中狀態已更新
        """
        emp = approval_scenario["employee"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # Step 1 & 2: 員工提交費用申請，確認 PENDING
        create_resp = client.post(
            "/approvals/expense",
            json=_EXPENSE,
            headers=auth_headers(emp_token),
        )
        assert create_resp.status_code == 200
        request_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "PENDING"

        # Step 3: 員工取消申請
        cancel_resp = client.post(
            f"/approvals/{request_id}/cancel",
            headers=auth_headers(emp_token),
        )
        assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"

        # Step 4: 確認狀態為 CANCELLED
        detail_resp = client.get(
            f"/approvals/{request_id}", headers=auth_headers(emp_token)
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "CANCELLED"

        # Step 5: 「我的申請」列表中狀態同步
        my_resp = client.get(
            "/approvals/my-requests?page=1&size=10", headers=auth_headers(emp_token)
        )
        assert my_resp.status_code == 200
        items = my_resp.json()["items"]
        cancelled_item = next((i for i in items if i["id"] == request_id), None)
        assert cancelled_item is not None
        assert cancelled_item["status"] == "CANCELLED"

    def test_cancelled_request_not_in_pending_list(self, client, approval_scenario):
        """
        旅程：員工取消申請後，Admin 的待核准列表不應出現該申請。
        """
        emp = approval_scenario["employee"]
        admin_token = approval_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # 提交並立即取消
        create_resp = client.post(
            "/approvals/leave", json=_SICK_LEAVE, headers=auth_headers(emp_token)
        )
        assert create_resp.status_code == 200
        request_id = create_resp.json()["id"]

        client.post(f"/approvals/{request_id}/cancel", headers=auth_headers(emp_token))

        # Admin 的待核准列表不應包含已取消的申請
        pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert pending_resp.status_code == 200
        pending_ids = [item["id"] for item in pending_resp.json()["items"]]
        assert request_id not in pending_ids


class TestRejectFlow:
    """測試拒絕申請流程：PENDING → REJECTED。"""

    def test_admin_rejects_leave_request(self, client, approval_scenario):
        """
        完整旅程：員工提交病假 → Admin 拒絕（含原因）→ 員工確認 REJECTED。

        Step 1: 員工提交病假申請
        Step 2: Admin 拒絕申請，附上原因
        Step 3: 員工確認狀態為 REJECTED
        Step 4: REJECTED 申請從 Admin 待核准列表消失
        """
        emp = approval_scenario["employee"]
        admin_token = approval_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # Step 1: 員工提交病假
        create_resp = client.post(
            "/approvals/leave",
            json=_SICK_LEAVE,
            headers=auth_headers(emp_token),
        )
        assert create_resp.status_code == 200
        request_id = create_resp.json()["id"]

        # Step 2: Admin 拒絕
        reject_resp = client.post(
            f"/approvals/{request_id}/reject",
            json={"comment": "文件不齊全，請補充醫師診斷書"},
            headers=auth_headers(admin_token),
        )
        assert reject_resp.status_code == 200, f"Reject failed: {reject_resp.text}"

        # Step 3: 員工確認狀態為 REJECTED
        detail_resp = client.get(
            f"/approvals/{request_id}", headers=auth_headers(emp_token)
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["status"] == "REJECTED"

        # Step 4: 申請從 Admin 待核准列表消失
        pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert pending_resp.status_code == 200
        pending_ids = [item["id"] for item in pending_resp.json()["items"]]
        assert request_id not in pending_ids


class TestMixedStatusJourney:
    """測試同一員工管理多個不同狀態申請的場景。"""

    def test_employee_manages_multiple_requests(self, client, approval_scenario):
        """
        完整旅程：員工同時持有 APPROVED、CANCELLED、REJECTED 三種狀態的申請。

        Step 1: 員工提交三個申請（兩請假、一費用）
        Step 2: Admin 核准第一個請假
        Step 3: 員工取消費用申請
        Step 4: Admin 拒絕第二個請假
        Step 5: 確認「我的申請」包含三種狀態
        """
        emp = approval_scenario["employee"]
        admin_token = approval_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # Step 1: 提交三個申請
        annual_resp = client.post(
            "/approvals/leave", json=_ANNUAL_LEAVE, headers=auth_headers(emp_token)
        )
        assert annual_resp.status_code == 200
        annual_id = annual_resp.json()["id"]

        expense_resp = client.post(
            "/approvals/expense", json=_EXPENSE, headers=auth_headers(emp_token)
        )
        assert expense_resp.status_code == 200
        expense_id = expense_resp.json()["id"]

        sick_resp = client.post(
            "/approvals/leave", json=_SICK_LEAVE, headers=auth_headers(emp_token)
        )
        assert sick_resp.status_code == 200
        sick_id = sick_resp.json()["id"]

        # Step 2: Admin 核准年假
        approve_resp = client.post(
            f"/approvals/{annual_id}/approve",
            json={"comment": "核准"},
            headers=auth_headers(admin_token),
        )
        assert approve_resp.status_code == 200

        # Step 3: 員工取消費用申請
        cancel_resp = client.post(
            f"/approvals/{expense_id}/cancel", headers=auth_headers(emp_token)
        )
        assert cancel_resp.status_code == 200

        # Step 4: Admin 拒絕病假
        reject_resp = client.post(
            f"/approvals/{sick_id}/reject",
            json={"comment": "文件不足"},
            headers=auth_headers(admin_token),
        )
        assert reject_resp.status_code == 200

        # Step 5: 確認三種狀態
        my_resp = client.get(
            "/approvals/my-requests?page=1&size=10", headers=auth_headers(emp_token)
        )
        assert my_resp.status_code == 200
        items = my_resp.json()["items"]
        assert my_resp.json()["total"] == 3

        statuses = {item["id"]: item["status"] for item in items}
        assert statuses[annual_id] == "APPROVED"
        assert statuses[expense_id] == "CANCELLED"
        assert statuses[sick_id] == "REJECTED"

    def test_approval_status_filter(self, client, approval_scenario):
        """
        旅程：提交多個申請後，依狀態篩選可得到正確結果。
        """
        emp = approval_scenario["employee"]
        admin_token = approval_scenario["admin_token"]
        emp_token = get_auth_token(client, emp["uid"], emp["password"])

        # 建立兩個申請：一個 PENDING、一個 APPROVED
        pending_resp = client.post(
            "/approvals/expense", json=_EXPENSE, headers=auth_headers(emp_token)
        )
        assert pending_resp.status_code == 200
        pending_id = pending_resp.json()["id"]

        annual_resp = client.post(
            "/approvals/leave", json=_ANNUAL_LEAVE, headers=auth_headers(emp_token)
        )
        assert annual_resp.status_code == 200
        annual_id = annual_resp.json()["id"]

        # Admin 核准年假
        client.post(
            f"/approvals/{annual_id}/approve",
            json={"comment": "核准"},
            headers=auth_headers(admin_token),
        )

        # 篩選 PENDING 申請（只應有費用申請）
        pending_filter_resp = client.get(
            "/approvals/my-requests?page=1&size=10&status=PENDING",
            headers=auth_headers(emp_token),
        )
        assert pending_filter_resp.status_code == 200
        pending_items = pending_filter_resp.json()["items"]
        pending_item_ids = [i["id"] for i in pending_items]
        assert pending_id in pending_item_ids
        assert annual_id not in pending_item_ids

        # 篩選 APPROVED 申請（只應有年假申請）
        approved_filter_resp = client.get(
            "/approvals/my-requests?page=1&size=10&status=APPROVED",
            headers=auth_headers(emp_token),
        )
        assert approved_filter_resp.status_code == 200
        approved_items = approved_filter_resp.json()["items"]
        approved_item_ids = [i["id"] for i in approved_items]
        assert annual_id in approved_item_ids
        assert pending_id not in approved_item_ids

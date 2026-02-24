"""
E2E 測試：新員工入職完整旅程。

測試跨功能的完整使用者旅程：
1. Admin 將一般使用者指派為員工
2. 員工建立工作排程
3. 員工提交請假申請
4. Admin 查看待核准列表並核准申請
5. 員工確認申請狀態已更新為 APPROVED

此測試橫跨 employee、schedule、approval 三個功能模組，
驗證系統各元件在真實使用情境下的整合正確性。
"""

from tests.e2e.conftest import get_auth_token, auth_headers


class TestNewEmployeeOnboardingJourney:
    """新員工入職全流程端對端測試。"""

    def test_full_onboarding_to_leave_approval(self, client, seed_admin, seed_normal_user):
        """
        完整旅程：指派員工 → 建立排程 → 提交請假 → Admin 核准 → 確認 APPROVED。

        Step 1: Admin 指派一般使用者為員工
        Step 2: 員工建立工作排程
        Step 3: 員工確認排程可查詢
        Step 4: 員工提交年假申請
        Step 5: 員工查看「我的申請」確認 PENDING 狀態
        Step 6: Admin 查看待核准列表，確認申請出現
        Step 7: Admin 核准申請
        Step 8: 員工確認申請狀態為 APPROVED
        Step 9: APPROVED 申請從 Admin 的待核准列表消失
        """
        # Step 1: Admin 指派員工
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])
        assign_resp = client.post(
            "/employees/assign",
            json={
                "user_id": seed_normal_user["id"],
                "idno": "EMP-E2E-001",
                "department": "IT",
                "role_id": 0,
            },
            headers=auth_headers(admin_token),
        )
        assert assign_resp.status_code == 200, f"Assign employee failed: {assign_resp.text}"
        emp_data = assign_resp.json()
        assert emp_data["idno"] == "EMP-E2E-001"
        assert emp_data["department"] == "IT"

        # Step 2: 員工登入並建立排程
        emp_token = get_auth_token(client, seed_normal_user["uid"], seed_normal_user["password"])
        schedule_resp = client.post(
            "/schedules/",
            json={
                "title": "入職訓練",
                "description": "新員工入職培訓課程",
                "location": "Training Room B",
                "start_time": "2026-03-01T09:00:00",
                "end_time": "2026-03-01T17:00:00",
                "all_day": False,
                "timezone": "Asia/Taipei",
                "sync_to_google": False,
            },
            headers=auth_headers(emp_token),
        )
        assert schedule_resp.status_code == 200, f"Create schedule failed: {schedule_resp.text}"
        schedule = schedule_resp.json()
        assert schedule["title"] == "入職訓練"
        schedule_id = schedule["id"]

        # Step 3: 確認排程可透過 ID 查詢
        get_schedule_resp = client.get(
            f"/schedules/{schedule_id}", headers=auth_headers(emp_token)
        )
        assert get_schedule_resp.status_code == 200
        assert get_schedule_resp.json()["id"] == schedule_id
        assert get_schedule_resp.json()["location"] == "Training Room B"

        # Step 4: 員工提交年假申請
        leave_resp = client.post(
            "/approvals/leave",
            json={
                "leave_type": "ANNUAL",
                "start_date": "2026-04-01T09:00:00",
                "end_date": "2026-04-03T18:00:00",
                "reason": "入職後首次年假",
            },
            headers=auth_headers(emp_token),
        )
        assert leave_resp.status_code == 200, f"Create leave request failed: {leave_resp.text}"
        leave_data = leave_resp.json()
        assert leave_data["status"] == "PENDING"
        assert leave_data["type"] == "LEAVE"
        assert leave_data["requester_id"] == seed_normal_user["id"]
        request_id = leave_data["id"]

        # Step 5: 員工查看「我的申請」，確認申請存在且狀態為 PENDING
        my_req_resp = client.get(
            "/approvals/my-requests?page=1&size=10", headers=auth_headers(emp_token)
        )
        assert my_req_resp.status_code == 200
        my_req_data = my_req_resp.json()
        assert my_req_data["total"] == 1
        assert my_req_data["items"][0]["status"] == "PENDING"
        assert my_req_data["items"][0]["type"] == "LEAVE"

        # Step 6: Admin 查看待核准列表，確認申請出現
        pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert pending_resp.status_code == 200
        pending_data = pending_resp.json()
        assert pending_data["total"] >= 1
        pending_ids = [item["id"] for item in pending_data["items"]]
        assert request_id in pending_ids

        # Step 7: Admin 核准申請
        approve_resp = client.post(
            f"/approvals/{request_id}/approve",
            json={"comment": "核准，祝旅途愉快！"},
            headers=auth_headers(admin_token),
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"

        # Step 8: 員工確認申請狀態為 APPROVED
        detail_resp = client.get(
            f"/approvals/{request_id}", headers=auth_headers(emp_token)
        )
        assert detail_resp.status_code == 200
        final_data = detail_resp.json()
        assert final_data["status"] == "APPROVED"
        assert final_data["type"] == "LEAVE"

        # 確認「我的申請」列表中狀態同步更新
        updated_my_req_resp = client.get(
            "/approvals/my-requests?page=1&size=10", headers=auth_headers(emp_token)
        )
        assert updated_my_req_resp.status_code == 200
        updated_items = updated_my_req_resp.json()["items"]
        approved_item = next(
            (item for item in updated_items if item["id"] == request_id), None
        )
        assert approved_item is not None
        assert approved_item["status"] == "APPROVED"

        # Step 9: APPROVED 申請從 Admin 待核准列表消失
        after_approve_pending_resp = client.get(
            "/approvals/pending?page=1&size=20", headers=auth_headers(admin_token)
        )
        assert after_approve_pending_resp.status_code == 200
        remaining_ids = [
            item["id"] for item in after_approve_pending_resp.json()["items"]
        ]
        assert request_id not in remaining_ids

    def test_admin_can_view_employee_list_after_assignment(
        self, client, seed_admin, seed_normal_user
    ):
        """
        旅程：指派員工後，Admin 可在員工列表中看到新員工。
        """
        admin_token = get_auth_token(client, seed_admin["uid"], seed_admin["password"])

        # 指派員工
        client.post(
            "/employees/assign",
            json={
                "user_id": seed_normal_user["id"],
                "idno": "EMP-E2E-002",
                "department": "HR",
                "role_id": 0,
            },
            headers=auth_headers(admin_token),
        )

        # Admin 查看員工列表
        list_resp = client.get(
            "/employees/?page=1&size=10", headers=auth_headers(admin_token)
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1
        idnos = [emp["idno"] for emp in list_data["items"]]
        assert "EMP-E2E-002" in idnos

"""
Integration tests: Workflow stub endpoint.

WorkFlowRouter currently exists but is NOT registered in app/router/__init__.py,
so the /workflows/create endpoint returns 404.

These tests document the current state and will need updating once
WorkFlowRouter is integrated into the main router.
"""
import pytest


class TestWorkflowRouterNotYetRegistered:
    """
    WorkFlowRouter is a stub that is not yet registered in the main router.
    Tests verify that the endpoint returns 404 (expected current behavior).
    Once the router is registered, these tests should be updated.
    """

    def test_create_workflow_returns_404_not_registered(self, client):
        """POST /workflows/create 回傳 404，因為 WorkFlowRouter 尚未注冊。"""
        payload = {"name": "Approval Flow", "steps": [{"action": "review"}]}
        resp = client.post("/workflows/create", json=payload)
        # WorkFlowRouter is not included in app/router/__init__.py
        assert resp.status_code == 404

    def test_create_workflow_empty_body_also_returns_404(self, client):
        """空 body 也回傳 404（路由未注冊）。"""
        resp = client.post("/workflows/create", json={})
        assert resp.status_code == 404

from __future__ import annotations

import json
from unittest.mock import Mock
import pytest
from workbench.server import WorkbenchRequestHandler


def test_cors_host_and_origin_verification() -> None:
    handler = Mock(spec=WorkbenchRequestHandler)
    handler.headers = {"Host": "malicious.com", "Origin": "http://malicious-origin.com"}
    handler.command = "GET"
    handler.path = "/health"
    handler.wfile = Mock()
    
    # Bind the real method to the mock instance
    handler._handle = WorkbenchRequestHandler._handle.__get__(handler, WorkbenchRequestHandler)
    handler._send_common_headers = Mock()
    
    # Run the handler
    handler._handle()
    
    # Assert response was 400 Bad Request
    handler.send_response.assert_called_with(400)
    
    # Verify wfile.write payload
    handler.wfile.write.assert_called()
    payload = json.loads(handler.wfile.write.call_args[0][0].decode("utf-8"))
    assert payload["ok"] is False
    assert "CORS check failed" in payload["error"]


def test_cors_loopback_host_and_origin_allowed() -> None:
    handler = Mock(spec=WorkbenchRequestHandler)
    handler.headers = {"Host": "127.0.0.1:8765", "Origin": "http://localhost:5173"}
    handler.command = "GET"
    handler.path = "/health"
    handler.wfile = Mock()
    handler.api = Mock()
    handler.api.handle.return_value = Mock(status=200, payload={"ok": True})
    
    # Bind the real method
    handler._handle = WorkbenchRequestHandler._handle.__get__(handler, WorkbenchRequestHandler)
    handler._send_common_headers = Mock()
    
    # Run the handler
    handler._handle()
    
    # Assert response was 200 OK (not 400)
    handler.send_response.assert_called_with(200)

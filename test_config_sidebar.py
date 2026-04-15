"""Tests for config_sidebar (no app.py import — avoids heavy optional deps in minimal envs)."""

import os
import sys
from unittest.mock import patch

import jwt

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config_sidebar import get_app_token, sign_app_access_jwt


def test_sign_app_access_jwt_roundtrip():
    aid = "69d216d0639800db95c6a7f8"
    secret = "test_secret_value_32_bytes_long!!"
    token = sign_app_access_jwt(aid, secret)
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    assert decoded["_appId"] == aid
    assert "iat" in decoded and "exp" in decoded


def test_get_app_token_parses_wrapped_result():
    mock_resp = type("R", (), {})()
    mock_resp.json = lambda: {
        "code": 200,
        "result": {"appToken": "tb_token_abc", "expire": 7200},
    }
    mock_resp.status_code = 200

    with patch("config_sidebar.requests.post", return_value=mock_resp):
        assert get_app_token("aid", "secret") == "tb_token_abc"


def test_get_app_token_flat_app_token():
    mock_resp = type("R", (), {})()
    mock_resp.json = lambda: {"code": 200, "appToken": "flat_token"}
    mock_resp.status_code = 200

    with patch("config_sidebar.requests.post", return_value=mock_resp):
        assert get_app_token("a", "b") == "flat_token"

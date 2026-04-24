"""
Unit tests for translating manifest access auth into Playwright kwargs.
"""

from __future__ import annotations

import pytest
from evaluate_agent.driver.auth import (
    MissingAuthEnvVar,
    context_kwargs_for,
)
from evaluate_agent.manifest.schema import WebAccess


def _access(auth: dict | None) -> WebAccess:
    data: dict = {"url": "https://example.com/chat"}
    if auth is not None:
        data["auth"] = auth
    return WebAccess.model_validate(data)


class TestNoAuth:
    def test_returns_empty_dict(self) -> None:
        kwargs = context_kwargs_for(_access(None))
        assert kwargs == {}


class TestBearer:
    def test_reads_env_and_builds_authorization_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TOK", "abc")
        kwargs = context_kwargs_for(
            _access(
                {
                    "type": "bearer",
                    "token_env": "TOK",
                }
            )
        )
        assert kwargs == {
            "extra_http_headers": {
                "Authorization": "Bearer abc"
            }
        }

    def test_raises_when_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TOK", raising=False)
        with pytest.raises(MissingAuthEnvVar, match="TOK"):
            context_kwargs_for(
                _access(
                    {
                        "type": "bearer",
                        "token_env": "TOK",
                    }
                )
            )


class TestBasic:
    def test_reads_both_envs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("U", "alice")
        monkeypatch.setenv("P", "secret")
        kwargs = context_kwargs_for(
            _access(
                {
                    "type": "basic",
                    "username_env": "U",
                    "password_env": "P",
                }
            )
        )
        assert kwargs == {
            "http_credentials": {
                "username": "alice",
                "password": "secret",
            }
        }

    def test_raises_when_username_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("U", raising=False)
        monkeypatch.setenv("P", "secret")
        with pytest.raises(MissingAuthEnvVar, match="U"):
            context_kwargs_for(
                _access(
                    {
                        "type": "basic",
                        "username_env": "U",
                        "password_env": "P",
                    }
                )
            )

    def test_raises_when_password_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("U", "alice")
        monkeypatch.delenv("P", raising=False)
        with pytest.raises(MissingAuthEnvVar, match="P"):
            context_kwargs_for(
                _access(
                    {
                        "type": "basic",
                        "username_env": "U",
                        "password_env": "P",
                    }
                )
            )

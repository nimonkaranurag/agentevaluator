"""Unit tests for the manifest schema.

These cover the non-obvious invariants the type system alone does not
enforce: unique case ids, catalog cross-validation, disjoint must/must_not,
strict extra-key rejection."""

from __future__ import annotations

import pytest
from evaluate_agent.manifest.schema import AgentManifest
from pydantic import ValidationError


def _minimal_manifest_dict() -> dict:
    """A manifest that satisfies every required field and nothing more.

    Tests mutate copies of this to assert specific failure modes.
    """
    return {
        "name": "sample-agent",
        "access": {"url": "https://agent.example.com/chat"},
        "cases": [
            {"id": "case_one", "input": "hello"},
        ],
    }


class TestHappyPath:
    def test_minimal_manifest_validates(self) -> None:
        m = AgentManifest.model_validate(
            _minimal_manifest_dict()
        )
        assert m.name == "sample-agent"
        assert len(m.cases) == 1
        assert m.cases[0].id == "case_one"
        assert m.observability.langfuse is None
        assert m.tools_catalog == []

    def test_fully_populated_manifest_validates(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["description"] = "Does things."
        data["access"]["auth"] = {
            "type": "bearer",
            "token_env": "TOK",
        }
        data["observability"] = {
            "langfuse": {
                "host": "https://cloud.langfuse.com"
            }
        }
        data["tools_catalog"] = ["a_tool", "b.tool"]
        data["agents_catalog"] = ["sub-agent"]
        data["cases"] = [
            {
                "id": "case1",
                "input": "do the thing",
                "assertions": {
                    "must_call": ["a_tool"],
                    "must_not_call": ["b.tool"],
                    "must_route_to": "sub-agent",
                    "max_steps": 3,
                    "final_response_contains": "done",
                },
            },
        ]
        m = AgentManifest.model_validate(data)
        assert m.cases[0].assertions.max_steps == 3
        assert m.access.auth is not None
        assert m.observability.langfuse is not None


class TestAgentName:
    @pytest.mark.parametrize(
        "bad_name",
        [
            "Upper",
            "has space",
            "9leading-digit",
            "",
            "-hyphen-first",
            "dot.name",
        ],
    )
    def test_invalid_agent_names_rejected(
        self, bad_name: str
    ) -> None:
        data = _minimal_manifest_dict()
        data["name"] = bad_name
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)

    @pytest.mark.parametrize(
        "good_name", ["a", "ok-name", "under_score", "x9"]
    )
    def test_valid_agent_names_accepted(
        self, good_name: str
    ) -> None:
        data = _minimal_manifest_dict()
        data["name"] = good_name
        m = AgentManifest.model_validate(data)
        assert m.name == good_name


class TestCases:
    def test_cases_must_not_be_empty(self) -> None:
        data = _minimal_manifest_dict()
        data["cases"] = []
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)

    def test_case_ids_must_be_unique(self) -> None:
        data = _minimal_manifest_dict()
        data["cases"] = [
            {"id": "dup", "input": "a"},
            {"id": "dup", "input": "b"},
        ]
        with pytest.raises(
            ValidationError, match="duplicate case ids"
        ):
            AgentManifest.model_validate(data)

    def test_case_input_must_not_be_empty(self) -> None:
        data = _minimal_manifest_dict()
        data["cases"][0]["input"] = ""
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)

    def test_max_steps_must_be_positive(self) -> None:
        data = _minimal_manifest_dict()
        data["cases"][0]["assertions"] = {"max_steps": 0}
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)


class TestCatalogCrossValidation:
    def test_must_call_must_reference_declared_tool(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["tools_catalog"] = ["known"]
        data["cases"][0]["assertions"] = {
            "must_call": ["unknown"]
        }
        with pytest.raises(
            ValidationError, match="undeclared tool"
        ):
            AgentManifest.model_validate(data)

    def test_must_not_call_must_reference_declared_tool(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["tools_catalog"] = ["known"]
        data["cases"][0]["assertions"] = {
            "must_not_call": ["unknown"]
        }
        with pytest.raises(
            ValidationError, match="undeclared tool"
        ):
            AgentManifest.model_validate(data)

    def test_must_route_to_must_reference_declared_agent(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["agents_catalog"] = ["known"]
        data["cases"][0]["assertions"] = {
            "must_route_to": "unknown"
        }
        with pytest.raises(
            ValidationError, match="undeclared agent"
        ):
            AgentManifest.model_validate(data)

    def test_empty_catalog_disables_cross_validation(
        self,
    ) -> None:
        """When a catalog is empty we have no knowledge of the agent's real
        surface, so we do not second-guess the assertions.
        """
        data = _minimal_manifest_dict()
        data["cases"][0]["assertions"] = {
            "must_call": ["anything_goes"]
        }
        m = AgentManifest.model_validate(data)
        assert m.cases[0].assertions.must_call == [
            "anything_goes"
        ]


class TestAssertionConsistency:
    def test_must_call_and_must_not_call_cannot_overlap(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["cases"][0]["assertions"] = {
            "must_call": ["t1", "t2"],
            "must_not_call": ["t2"],
        }
        with pytest.raises(
            ValidationError, match="overlap"
        ):
            AgentManifest.model_validate(data)


class TestAccess:
    def test_non_http_url_rejected(self) -> None:
        data = _minimal_manifest_dict()
        data["access"]["url"] = "ftp://example.com"
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)

    def test_bearer_auth_requires_token_env(self) -> None:
        data = _minimal_manifest_dict()
        data["access"]["auth"] = {"type": "bearer"}
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)

    def test_basic_auth_requires_both_env_vars(
        self,
    ) -> None:
        data = _minimal_manifest_dict()
        data["access"]["auth"] = {
            "type": "basic",
            "username_env": "U",
        }
        with pytest.raises(ValidationError):
            AgentManifest.model_validate(data)


class TestStrictness:
    def test_unknown_top_level_key_rejected(self) -> None:
        data = _minimal_manifest_dict()
        data["typo_field"] = "oops"
        with pytest.raises(
            ValidationError, match="[Ee]xtra"
        ):
            AgentManifest.model_validate(data)

    def test_unknown_assertion_key_rejected(self) -> None:
        data = _minimal_manifest_dict()
        data["cases"][0]["assertions"] = {
            "must_calll": ["t"]
        }  # typo
        with pytest.raises(
            ValidationError, match="[Ee]xtra"
        ):
            AgentManifest.model_validate(data)

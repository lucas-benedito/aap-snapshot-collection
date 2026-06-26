"""Unit tests for parse_aap_version filter plugin."""

import os
import sys
import types

import pytest

# Mock ansible.errors before importing the filter
_mock_ansible = types.ModuleType("ansible")
_mock_errors = types.ModuleType("ansible.errors")


class _AnsibleFilterError(Exception):
    pass


_mock_errors.AnsibleFilterError = _AnsibleFilterError
_mock_ansible.errors = _mock_errors
sys.modules["ansible"] = _mock_ansible
sys.modules["ansible.errors"] = _mock_errors

import importlib.util

_filter_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "plugins",
    "filter",
    "aap_version.py",
)
_spec = importlib.util.spec_from_file_location("aap_version_filter", _filter_path)
aap_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aap_version)


class TestParseAapVersion:
    def test_three_part_version(self):
        result = aap_version.parse_aap_version("2.6.3")
        assert result["major"] == "2"
        assert result["minor"] == "6"
        assert result["patch"] == "3"
        assert result["major_minor"] == "2.6"
        assert result["full"] == "2.6.3"
        assert "timestamp" not in result

    def test_two_part_version(self):
        result = aap_version.parse_aap_version("2.7")
        assert result["major"] == "2"
        assert result["minor"] == "7"
        assert result["patch"] == "0"
        assert result["major_minor"] == "2.7"

    def test_prerelease_version(self):
        result = aap_version.parse_aap_version("2.6.3-rc1")
        assert result["major"] == "2"
        assert result["minor"] == "6"
        assert result["patch"] == "3"

    def test_postgresql_style_version(self):
        result = aap_version.parse_aap_version("15.2")
        assert result["major"] == "15"
        assert result["minor"] == "2"
        assert result["patch"] == "0"

    def test_operator_csv_namespace_scoped(self):
        result = aap_version.parse_aap_version("aap-operator.v2.6.0-0.1777410689")
        assert result["major"] == "2"
        assert result["minor"] == "6"
        assert result["patch"] == "0"
        assert result["major_minor"] == "2.6"
        assert result["timestamp"] == "1777410689"

    def test_operator_csv_cluster_scoped(self):
        result = aap_version.parse_aap_version("aap-operator.v2.6.0-0.1777410680")
        assert result["major"] == "2"
        assert result["minor"] == "6"
        assert result["patch"] == "0"
        assert result["timestamp"] == "1777410680"

    def test_operator_csv_preserves_full(self):
        result = aap_version.parse_aap_version("aap-operator.v2.6.0-0.1777410689")
        assert result["full"] == "aap-operator.v2.6.0-0.1777410689"

    def test_whitespace_stripped(self):
        result = aap_version.parse_aap_version("  2.6.3  ")
        assert result["major_minor"] == "2.6"

    def test_non_string_raises(self):
        with pytest.raises(_AnsibleFilterError, match="expects a string"):
            aap_version.parse_aap_version(123)

    def test_empty_string_raises(self):
        with pytest.raises(_AnsibleFilterError, match="Cannot parse"):
            aap_version.parse_aap_version("")

    def test_garbage_raises(self):
        with pytest.raises(_AnsibleFilterError, match="Cannot parse"):
            aap_version.parse_aap_version("not-a-version")

    def test_filter_module_exports(self):
        fm = aap_version.FilterModule()
        filters = fm.filters()
        assert "parse_aap_version" in filters

"""Unit tests for langgraph.utils.type_guards."""

import pytest


def test_is_non_empty_dict_with_non_empty():
    from langgraph.utils.type_guards import is_non_empty_dict
    assert is_non_empty_dict({"key": "value"}) is True


def test_is_non_empty_dict_with_empty():
    from langgraph.utils.type_guards import is_non_empty_dict
    assert is_non_empty_dict({}) is False


def test_is_non_empty_dict_with_non_dict():
    from langgraph.utils.type_guards import is_non_empty_dict
    assert is_non_empty_dict([1, 2, 3]) is False
    assert is_non_empty_dict("string") is False
    assert is_non_empty_dict(None) is False

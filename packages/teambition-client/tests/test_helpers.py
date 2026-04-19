import pytest

from teambition_client.helpers import api_result_list, coerce_api_json_dict, merge_snake_to_camel_for_path


def test_merge_snake_to_camel():
    ctx = merge_snake_to_camel_for_path({"project_id": "p1"})
    assert ctx["projectId"] == "p1"


def test_api_result_list_none_result():
    assert api_result_list({"result": None}) == []


def test_coerce_json_dict_python_literal():
    d = coerce_api_json_dict("{'pageSize': 50}", "default_params")
    assert d == {"pageSize": 50}


def test_coerce_invalid():
    with pytest.raises(ValueError):
        coerce_api_json_dict("[1,2]", "x")

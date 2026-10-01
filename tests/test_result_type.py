import pytest
from core.shared.result import Result, Ok, Err, UnwrapFailedError


def test_ok_creation_and_properties():
    res = Ok("hello")
    assert res.is_ok() is True
    assert res.is_err() is False
    assert res.ok is True
    assert res.data == "hello"
    assert res.error is None
    assert res.warnings == []
    assert res.has_warnings() is False
    assert res.unwrap() == "hello"
    assert res.unwrap_or("fallback") == "hello"
    assert res.expect("Should not fail") == "hello"


def test_err_creation_and_properties():
    res = Err("disk failure")
    assert res.is_ok() is False
    assert res.is_err() is True
    assert res.ok is False
    assert res.data is None
    assert res.error == "disk failure"
    assert res.warnings == []
    assert res.has_warnings() is False
    assert res.unwrap_or("fallback") == "fallback"
    
    with pytest.raises(UnwrapFailedError) as exc_info:
        res.unwrap()
    assert "disk failure" in str(exc_info.value)

    with pytest.raises(UnwrapFailedError) as exc_info:
        res.expect("Custom expectation failure")
    assert "Custom expectation failure: disk failure" in str(exc_info.value)


def test_warnings_support():
    res = Ok("success_val").with_warning("Warning 1").with_warning("Warning 2")
    assert res.is_ok() is True
    assert res.has_warnings() is True
    assert res.warnings == ["Warning 1", "Warning 2"]
    assert res.unwrap() == "success_val"

    err = Err("failed_val").with_warning("Err Warning")
    assert err.is_err() is True
    assert err.has_warnings() is True
    assert err.warnings == ["Err Warning"]


def test_combinator_map():
    res = Ok(10).with_warning("w1").map(lambda x: x * 2)
    assert res.is_ok() is True
    assert res.unwrap() == 20
    assert res.warnings == ["w1"]

    err = Err("err_msg").with_warning("w2").map(lambda x: x * 2)
    assert err.is_err() is True
    assert err.error == "err_msg"
    assert err.warnings == ["w2"]


def test_combinator_map_err():
    res = Ok(10).map_err(lambda e: f"Prefix: {e}")
    assert res.is_ok() is True
    assert res.unwrap() == 10

    err = Err("404").with_warning("w3").map_err(lambda e: f"Error: {e}")
    assert err.is_err() is True
    assert err.error == "Error: 404"
    assert err.warnings == ["w3"]


def test_combinator_and_then():
    def double_if_positive(val: int) -> Result[int, str]:
        if val > 0:
            return Ok(val * 2).with_warning("positive doubled")
        return Err("val not positive")

    res = Ok(5).with_warning("initial").and_then(double_if_positive)
    assert res.is_ok() is True
    assert res.unwrap() == 10
    # Both warnings accumulated
    assert res.warnings == ["initial", "positive doubled"]

    res_fail = Ok(-1).with_warning("initial").and_then(double_if_positive)
    assert res_fail.is_err() is True
    assert res_fail.error == "val not positive"
    assert res_fail.warnings == ["initial"]

    err_skip = Err("already bad").with_warning("init_err").and_then(double_if_positive)
    assert err_skip.is_err() is True
    assert err_skip.error == "already bad"
    assert err_skip.warnings == ["init_err"]


def test_backward_compatibility():
    # Result.success(...)
    res1 = Result.success("legacy_data")
    assert res1.ok is True
    assert res1.data == "legacy_data"
    assert res1.error is None
    assert res1.warnings == []

    # Result.fail(...)
    res2 = Result.fail("legacy_error", data={"partial": True})
    assert res2.ok is False
    assert res2.error == "legacy_error"
    assert res2.data == {"partial": True}
    assert res2.warnings == []

    # Dict representation
    d1 = res1.to_dict()
    assert d1 == {"ok": True, "data": "legacy_data", "error": None, "warnings": []}

    d2 = res2.to_dict()
    assert d2 == {"ok": False, "data": {"partial": True}, "error": "legacy_error", "warnings": []}

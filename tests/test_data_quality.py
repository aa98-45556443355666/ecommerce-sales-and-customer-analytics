import pytest

from src.validation.validate_data import evaluate_count


def test_zero_issues_pass():
    assert evaluate_count(0) == "PASS"


def test_critical_issues_fail():
    assert evaluate_count(
        3,
        expectation="zero",
        severity="FAIL",
    ) == "FAIL"


def test_expected_dirty_data_generates_warning():
    assert evaluate_count(
        3,
        expectation="zero",
        severity="WARN",
    ) == "WARN"


def test_non_empty_table_passes():
    assert evaluate_count(
        100,
        expectation="positive",
    ) == "PASS"


def test_empty_table_fails():
    assert evaluate_count(
        0,
        expectation="positive",
    ) == "FAIL"


def test_negative_count_is_rejected():
    with pytest.raises(ValueError):
        evaluate_count(-1)


def test_invalid_expectation_is_rejected():
    with pytest.raises(ValueError):
        evaluate_count(0, expectation="negative")


def test_invalid_severity_is_rejected():
    with pytest.raises(ValueError):
        evaluate_count(1, severity="INFO")

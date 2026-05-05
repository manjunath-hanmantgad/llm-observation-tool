import pytest

from gateway.cost import calculate_cost


def test_mock_model_is_free() -> None:
    assert calculate_cost("mock-observatory-model", 100, 100) == 0


def test_known_model_cost() -> None:
    assert calculate_cost("gpt-4o-mini", 1000, 1000) == pytest.approx(0.00075)

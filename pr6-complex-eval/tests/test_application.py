import numpy as np
import pytest

from tsisa_complex_eval.application import (
    compute_complex_evaluation,
    normalize_matrix,
)
from tsisa_complex_eval.domain import (
    ComplexEvalConfig,
    Criterion,
    Direction,
    ExpertWeights,
)


@pytest.fixture
def simple_config():
    return ComplexEvalConfig(
        criteria=[
            Criterion("K1", "A", Direction.MAX),
            Criterion("K2", "B", Direction.MIN),
        ],
        experts=[
            ExpertWeights("E1", "student", (0.5, 0.5)),
            ExpertWeights("E2", "teacher", (0.5, 0.5)),
        ],
        alternatives=["A1", "A2"],
        alpha=0.5,
    )


def test_normalize_max_min():
    raw = np.array([[10.0, 2.0], [5.0, 4.0]])
    out = normalize_matrix(raw, [Direction.MAX, Direction.MIN])
    assert np.allclose(out, [[1.0, 1.0], [0.5, 0.5]])


def test_raises_on_zero_max():
    with pytest.raises(ValueError):
        normalize_matrix(np.array([[0.0]]), [Direction.MAX])


def test_compute_runs(simple_config):
    raw = np.array([[10.0, 2.0], [5.0, 4.0]])
    res = compute_complex_evaluation(raw, simple_config)
    assert len(res.ranking) == 2
    assert res.ranking[0][0] in {"A1", "A2"}


def test_weights_sum_to_one(simple_config):
    raw = np.array([[1.0, 1.0], [2.0, 2.0]])
    res = compute_complex_evaluation(raw, simple_config)
    assert np.isclose(res.w_combined.sum(), 1.0)

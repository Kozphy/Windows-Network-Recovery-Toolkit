"""Tests for interaction contrast mathematics."""

from research.interactions.analysis import interaction_contrast


def test_interaction_contrast_additive() -> None:
    # Y11 - Y10 - Y01 + Y00 = 1 - 0.5 - 0.5 + 0 = 0
    main_x1, main_x2, interaction = interaction_contrast(0.0, 0.5, 0.5, 1.0)
    assert abs(interaction) < 1e-9
    assert abs(main_x1 - 0.5) < 1e-9
    assert abs(main_x2 - 0.5) < 1e-9


def test_interaction_contrast_synergistic() -> None:
    # Designed synergy: 0.9 - 0.4 - 0.3 + 0 = 0.2
    _, _, interaction = interaction_contrast(0.0, 0.4, 0.3, 0.9)
    assert abs(interaction - 0.2) < 1e-9


def test_interaction_contrast_antagonistic() -> None:
    _, _, interaction = interaction_contrast(0.0, 0.6, 0.6, 0.8)
    assert interaction < 0

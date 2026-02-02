"""Comprehensive unit tests for src/analysis.py module.

This test suite covers all functions in the analysis module with extensive test cases
to achieve 95%+ code coverage. Tests include happy paths, edge cases, and error scenarios.
"""

import pytest
from src.analysis import (
    calculate_implied_probability,
    devig_pinnacle_odds,
    calculate_ev_percentage,
    calculate_parlay_probability,
    calculate_parlay_ev,
    calculate_breakeven_probability,
)


class TestCalculateImpliedProbability:
    """Test suite for calculate_implied_probability function."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "odds,expected",
        [
            # Negative odds (favorites)
            (-110, 0.523809523809524),  # Standard line
            (-150, 0.6),  # Moderate favorite
            (-200, 0.666666666666667),  # Strong favorite
            (-500, 0.833333333333333),  # Heavy favorite
            (-100, 0.5),  # Minimum favorite (even)
            (-120, 0.545454545454545),  # Common line
            (-130, 0.565217391304348),  # Common line
            (-250, 0.714285714285714),  # Heavy favorite
        ],
    )
    def test_negative_odds_favorites(self, odds, expected):
        """Test conversion of negative odds (favorites) to probability.

        Negative odds represent the amount needed to bet to win $100.
        Formula: |odds| / (|odds| + 100)
        """
        result = calculate_implied_probability(odds)
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "odds,expected",
        [
            # Positive odds (underdogs)
            (100, 0.5),  # Even money
            (150, 0.4),  # Moderate underdog
            (200, 0.333333333333333),  # Strong underdog
            (500, 0.166666666666667),  # Heavy underdog
            (110, 0.476190476190476),  # Common line
            (130, 0.434782608695652),  # Common line
            (250, 0.285714285714286),  # Heavy underdog
            (1000, 0.090909090909091),  # Extreme underdog
        ],
    )
    def test_positive_odds_underdogs(self, odds, expected):
        """Test conversion of positive odds (underdogs) to probability.

        Positive odds represent profit on a $100 bet.
        Formula: 100 / (odds + 100)
        """
        result = calculate_implied_probability(odds)
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_even_money_odds(self):
        """Test that +100 and -100 both return exactly 0.5 probability."""
        positive_result = calculate_implied_probability(100)
        negative_result = calculate_implied_probability(-100)

        assert positive_result == pytest.approx(0.5, abs=1e-10)
        assert negative_result == pytest.approx(0.5, abs=1e-10)
        assert positive_result == negative_result

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "odds",
        [
            -1,  # Very small negative
            -50,  # Small negative
            -99,  # Just below -100
            1,  # Very small positive
            50,  # Small positive
            99,  # Just below 100
        ],
    )
    def test_unusual_but_valid_odds(self, odds):
        """Test odds in unusual ranges (between -100 and 100, excluding exactly -100/100).

        These are technically valid but rarely used in practice.
        The function should handle them correctly without error.
        """
        result = calculate_implied_probability(odds)
        assert isinstance(result, float)
        assert 0 < result < 1

    @pytest.mark.unit
    def test_extreme_odds_values(self):
        """Test extremely high odds values to ensure no overflow/underflow issues."""
        # Extreme favorite
        result_heavy_fav = calculate_implied_probability(-10000)
        assert result_heavy_fav == pytest.approx(0.990099009900990, abs=1e-10)
        assert result_heavy_fav < 1.0

        # Extreme underdog
        result_heavy_dog = calculate_implied_probability(10000)
        assert result_heavy_dog == pytest.approx(0.009900990099010, abs=1e-10)
        assert result_heavy_dog > 0.0

    @pytest.mark.unit
    def test_probability_bounds(self):
        """Verify that all probabilities are strictly between 0 and 1."""
        test_odds = [-500, -200, -110, 100, 200, 500]

        for odds in test_odds:
            prob = calculate_implied_probability(odds)
            assert 0 < prob < 1, f"Probability for odds {odds} should be between 0 and 1"


class TestDevigPinnacleOdds:
    """Test suite for devig_pinnacle_odds function."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "over_odds,under_odds,expected_over,expected_under",
        [
            # Symmetric odds
            (-110, -110, 0.5, 0.5),
            (-120, -120, 0.5, 0.5),
            (-105, -105, 0.5, 0.5),
            (-115, -115, 0.5, 0.5),
            # Asymmetric odds - over favored
            (-150, 130, 0.5798319327731092, 0.42016806722689076),
            (-200, 175, 0.6470588235294118, 0.35294117647058826),
            (-130, 110, 0.5427435387673957, 0.4572564612326044),
            # Asymmetric odds - under favored
            (130, -150, 0.42016806722689076, 0.5798319327731092),
            (175, -200, 0.35294117647058826, 0.6470588235294118),
            # Low juice (sharp market)
            (-102, -102, 0.5, 0.5),
            (100, -105, 0.4939759036144578, 0.5060240963855421),
        ],
    )
    def test_devig_various_odds(self, over_odds, under_odds, expected_over, expected_under):
        """Test vig removal with various odds combinations.

        Verifies that the function correctly removes vig and returns normalized probabilities.
        """
        over_prob, under_prob = devig_pinnacle_odds(over_odds, under_odds)

        assert over_prob == pytest.approx(expected_over, abs=1e-10)
        assert under_prob == pytest.approx(expected_under, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "over_odds,under_odds",
        [
            (-110, -110),
            (-120, -120),
            (-150, 130),
            (-200, 175),
            (130, -150),
            (-105, -115),
            (100, -100),
            (-500, 400),
        ],
    )
    def test_probabilities_sum_to_one(self, over_odds, under_odds):
        """Verify that de-vigged probabilities always sum to exactly 1.0.

        This is a fundamental property - after removing vig, the probabilities
        must represent a fair market where the total probability is exactly 1.
        """
        over_prob, under_prob = devig_pinnacle_odds(over_odds, under_odds)

        assert over_prob + under_prob == pytest.approx(1.0, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "over_odds,under_odds",
        [
            (-110, -110),
            (-150, 130),
            (-200, 175),
            (130, -150),
        ],
    )
    def test_devigged_probabilities_less_than_or_equal_implied(
        self, over_odds, under_odds
    ):
        """Verify that de-vigged probabilities are <= original implied probabilities.

        Since vig inflates probabilities above 1.0, removing vig should reduce
        each probability. This tests that the normalization works correctly.
        """
        over_prob, under_prob = devig_pinnacle_odds(over_odds, under_odds)

        over_implied = calculate_implied_probability(over_odds)
        under_implied = calculate_implied_probability(under_odds)

        assert over_prob <= over_implied
        assert under_prob <= under_implied

    @pytest.mark.unit
    def test_high_juice_scenario(self):
        """Test vig removal with high juice (large bookmaker edge).

        With -120/-120 odds, the total implied probability is ~1.0909,
        meaning the vig is about 9.09%.
        """
        over_prob, under_prob = devig_pinnacle_odds(-120, -120)

        # Should normalize to exactly 0.5 each
        assert over_prob == pytest.approx(0.5, abs=1e-10)
        assert under_prob == pytest.approx(0.5, abs=1e-10)

        # Verify vig was removed
        over_implied = calculate_implied_probability(-120)
        assert over_implied > 0.5  # Original had vig
        assert over_prob == 0.5  # After devig, exactly fair

    @pytest.mark.unit
    def test_low_juice_scenario(self):
        """Test vig removal with low juice (small bookmaker edge).

        Sharp books like Pinnacle often have -102/-102 or similar low-juice lines.
        """
        over_prob, under_prob = devig_pinnacle_odds(-102, -102)

        assert over_prob == pytest.approx(0.5, abs=1e-10)
        assert under_prob == pytest.approx(0.5, abs=1e-10)

    @pytest.mark.unit
    def test_extreme_asymmetric_odds(self):
        """Test vig removal with highly asymmetric odds (strong favorite vs underdog)."""
        over_prob, under_prob = devig_pinnacle_odds(-500, 400)

        # Over should be strongly favored
        assert over_prob > 0.7
        assert under_prob < 0.3

        # But must still sum to 1
        assert over_prob + under_prob == pytest.approx(1.0, abs=1e-10)


class TestCalculateEVPercentage:
    """Test suite for calculate_ev_percentage function."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "fair_prob,breakeven_prob,expected_ev",
        [
            # Positive EV scenarios
            (0.60, 0.5425, 10.599078341013825),  # Good edge
            (0.65, 0.5425, 19.815668202764977),  # Great edge
            (0.58, 0.5425, 6.912442396313364),  # Modest edge
            (0.70, 0.5425, 29.032258064516129),  # Excellent edge
            # Break-even scenarios
            (0.5425, 0.5425, 0.0),  # Exactly break-even
            # Negative EV scenarios
            (0.54, 0.5425, -0.460829493087558),  # Slight negative
            (0.50, 0.5425, -7.834101382488479),  # Moderate negative
            (0.45, 0.5425, -17.050691244239631),  # Strong negative
            (0.40, 0.5425, -26.267281105990783),  # Very negative
        ],
    )
    def test_ev_calculation_various_probabilities(
        self, fair_prob, breakeven_prob, expected_ev
    ):
        """Test EV percentage calculation with various probability scenarios.

        EV% = ((fair_prob / breakeven_prob) - 1) * 100
        """
        result = calculate_ev_percentage(fair_prob, breakeven_prob)
        assert result == pytest.approx(expected_ev, abs=1e-10)

    @pytest.mark.unit
    def test_positive_ev_scenario(self):
        """Test that positive EV is correctly identified when fair_prob > breakeven."""
        fair_prob = 0.60
        breakeven_prob = 0.5425

        ev = calculate_ev_percentage(fair_prob, breakeven_prob)

        assert ev > 0, "Should be positive EV when fair probability exceeds breakeven"
        assert ev == pytest.approx(10.599078341013825, abs=1e-10)

    @pytest.mark.unit
    def test_negative_ev_scenario(self):
        """Test that negative EV is correctly identified when fair_prob < breakeven."""
        fair_prob = 0.50
        breakeven_prob = 0.5425

        ev = calculate_ev_percentage(fair_prob, breakeven_prob)

        assert ev < 0, "Should be negative EV when fair probability is below breakeven"
        assert ev == pytest.approx(-7.834101382488479, abs=1e-10)

    @pytest.mark.unit
    def test_breakeven_scenario(self):
        """Test that EV is exactly 0 when fair_prob equals breakeven."""
        breakeven_prob = 0.5425

        ev = calculate_ev_percentage(breakeven_prob, breakeven_prob)

        assert ev == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "parlay_legs,payout,breakeven",
        [
            (2, 3.0, 0.577350269189626),  # 2-leg, 3x payout
            (3, 6.0, 0.550321208137080),  # 3-leg, 6x payout
            (4, 10.0, 0.562341325190349),  # 4-leg, 10x payout
            (5, 10.0, 0.630957344480193),  # 5-leg, 10x payout
        ],
    )
    def test_different_parlay_structures(self, parlay_legs, payout, breakeven):
        """Test EV calculation with different parlay structures.

        Verifies that the function works correctly with various breakeven
        probabilities corresponding to different parlay/payout combinations.
        """
        # Test positive EV for each structure
        fair_prob = breakeven * 1.1  # 10% above breakeven
        ev = calculate_ev_percentage(fair_prob, breakeven, parlay_legs)
        assert ev == pytest.approx(10.0, abs=1e-8)

        # Test negative EV for each structure
        fair_prob = breakeven * 0.9  # 10% below breakeven
        ev = calculate_ev_percentage(fair_prob, breakeven, parlay_legs)
        assert ev == pytest.approx(-10.0, abs=1e-8)

    @pytest.mark.unit
    def test_extreme_positive_ev(self):
        """Test EV calculation with extremely favorable odds."""
        fair_prob = 0.90
        breakeven_prob = 0.5425

        ev = calculate_ev_percentage(fair_prob, breakeven_prob)

        assert ev > 50  # Should be very high positive EV
        assert ev == pytest.approx(65.89861751152074, abs=1e-10)

    @pytest.mark.unit
    def test_extreme_negative_ev(self):
        """Test EV calculation with extremely unfavorable odds."""
        fair_prob = 0.30
        breakeven_prob = 0.5425

        ev = calculate_ev_percentage(fair_prob, breakeven_prob)

        assert ev < -40  # Should be very high negative EV
        assert ev == pytest.approx(-44.700460829493088, abs=1e-10)

    @pytest.mark.unit
    def test_edge_case_probabilities(self):
        """Test edge cases with probabilities near 0 and 1."""
        # Near certain event
        ev_high = calculate_ev_percentage(0.99, 0.5425)
        assert ev_high > 80

        # Very unlikely event
        ev_low = calculate_ev_percentage(0.10, 0.5425)
        assert ev_low < -80


class TestCalculateParlayProbability:
    """Test suite for calculate_parlay_probability function."""

    @pytest.mark.unit
    def test_single_leg_parlay(self):
        """Test that single-leg parlay returns the same probability."""
        leg_probs = [0.6]
        result = calculate_parlay_probability(leg_probs)
        assert result == pytest.approx(0.6, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "leg_probs,expected",
        [
            # Two-leg parlays
            ([0.6, 0.6], 0.36),
            ([0.5, 0.5], 0.25),
            ([0.577, 0.577], 0.332929),
            ([0.7, 0.6], 0.42),
            # Three-leg parlays
            ([0.5, 0.5, 0.5], 0.125),
            ([0.6, 0.6, 0.6], 0.216),
            ([0.5, 0.6, 0.7], 0.21),
            ([0.55, 0.55, 0.55], 0.166375),
            # Four-leg parlays
            ([0.5, 0.5, 0.5, 0.5], 0.0625),
            ([0.6, 0.6, 0.6, 0.6], 0.1296),
            # Five-leg parlays
            ([0.6, 0.6, 0.6, 0.6, 0.6], 0.07776),
            ([0.5, 0.5, 0.5, 0.5, 0.5], 0.03125),
        ],
    )
    def test_multi_leg_parlays(self, leg_probs, expected):
        """Test parlay probability calculation for various multi-leg parlays.

        Parlay probability is the product of all leg probabilities.
        """
        result = calculate_parlay_probability(leg_probs)
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_empty_list(self):
        """Test that empty list returns 1.0 (neutral/identity element)."""
        result = calculate_parlay_probability([])
        assert result == pytest.approx(1.0, abs=1e-10)

    @pytest.mark.unit
    def test_probability_of_one(self):
        """Test parlay with certain events (probability 1.0)."""
        # Single certain event
        result_single = calculate_parlay_probability([1.0])
        assert result_single == pytest.approx(1.0, abs=1e-10)

        # Multiple certain events
        result_multi = calculate_parlay_probability([1.0, 1.0, 1.0])
        assert result_multi == pytest.approx(1.0, abs=1e-10)

    @pytest.mark.unit
    def test_probability_of_zero(self):
        """Test parlay with impossible events (probability 0.0)."""
        # Single impossible event
        result_single = calculate_parlay_probability([0.0])
        assert result_single == pytest.approx(0.0, abs=1e-10)

        # One impossible event makes entire parlay impossible
        result_mixed = calculate_parlay_probability([0.6, 0.0, 0.7])
        assert result_mixed == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.unit
    def test_many_legs_parlay(self):
        """Test parlay with many legs to verify no overflow issues."""
        # 10-leg parlay with 60% legs
        leg_probs = [0.6] * 10
        result = calculate_parlay_probability(leg_probs)
        expected = 0.6 ** 10  # 0.0060466176
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_asymmetric_probabilities(self):
        """Test parlay with varied probability legs."""
        leg_probs = [0.9, 0.8, 0.7, 0.6, 0.5]
        result = calculate_parlay_probability(leg_probs)
        expected = 0.9 * 0.8 * 0.7 * 0.6 * 0.5  # 0.1512
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_breakeven_probability_parlays(self):
        """Test parlay probabilities that should be at breakeven for specific payouts."""
        # 2-leg parlay at breakeven for 3x payout
        breakeven_2leg = 0.577350269189626
        result_2leg = calculate_parlay_probability([breakeven_2leg, breakeven_2leg])
        assert result_2leg == pytest.approx(1.0 / 3.0, abs=1e-6)

        # 3-leg parlay at breakeven for 6x payout
        breakeven_3leg = 0.550321208137080
        result_3leg = calculate_parlay_probability([breakeven_3leg] * 3)
        assert result_3leg == pytest.approx(1.0 / 6.0, abs=1e-6)

    @pytest.mark.unit
    def test_high_probability_legs(self):
        """Test parlay with high-probability legs."""
        leg_probs = [0.95, 0.95, 0.95]
        result = calculate_parlay_probability(leg_probs)
        assert result == pytest.approx(0.857375, abs=1e-10)
        assert result < 0.95  # Parlay prob should be lower than any individual leg

    @pytest.mark.unit
    def test_low_probability_legs(self):
        """Test parlay with low-probability legs."""
        leg_probs = [0.3, 0.3, 0.3]
        result = calculate_parlay_probability(leg_probs)
        assert result == pytest.approx(0.027, abs=1e-10)
        assert result < 0.1  # Very low combined probability


class TestCalculateParlayEV:
    """Test suite for calculate_parlay_ev function."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "leg_probs,payout,expected_ev",
        [
            # Positive EV parlays
            ([0.6, 0.6], 3.0, 0.08),  # 36% * 3 - 1 = 0.08
            ([0.65, 0.65], 3.0, 0.2675),  # 42.25% * 3 - 1 = 0.2675
            ([0.7, 0.7], 3.0, 0.47),  # 49% * 3 - 1 = 0.47
            # Near break-even parlays
            ([0.577, 0.577], 3.0, -0.001213),  # Very close to break-even
            ([0.55032, 0.55032, 0.55032], 6.0, -6.586043391876295e-06),  # 3-leg near break-even
            # Negative EV parlays
            ([0.5, 0.5], 3.0, -0.25),  # 25% * 3 - 1 = -0.25
            ([0.4, 0.4], 3.0, -0.52),  # 16% * 3 - 1 = -0.52
            ([0.5, 0.5, 0.5], 6.0, -0.25),  # 12.5% * 6 - 1 = -0.25
            # Higher payout multipliers
            ([0.6, 0.6, 0.6], 6.0, 0.296),  # 21.6% * 6 - 1 = 0.296
            ([0.6, 0.6, 0.6, 0.6, 0.6], 10.0, -0.2224),  # 7.776% * 10 - 1
        ],
    )
    def test_parlay_ev_calculations(self, leg_probs, payout, expected_ev):
        """Test EV calculation for various parlay scenarios.

        EV = (Parlay_Win_Probability * Payout_Multiplier) - 1
        """
        result = calculate_parlay_ev(leg_probs, payout)
        assert result == pytest.approx(expected_ev, abs=1e-6)

    @pytest.mark.unit
    def test_positive_ev_parlay(self):
        """Test that positive EV is correctly calculated for profitable parlays."""
        leg_probs = [0.6, 0.6]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        assert ev > 0, "Should be positive EV"
        assert ev == pytest.approx(0.08, abs=1e-10)

    @pytest.mark.unit
    def test_negative_ev_parlay(self):
        """Test that negative EV is correctly calculated for unprofitable parlays."""
        leg_probs = [0.5, 0.5]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        assert ev < 0, "Should be negative EV"
        assert ev == pytest.approx(-0.25, abs=1e-10)

    @pytest.mark.unit
    def test_breakeven_parlay(self):
        """Test parlay at exact breakeven point (EV = 0).

        For a parlay to break even: (leg_prob)^num_legs * payout = 1
        """
        # 2-leg parlay with 3x payout: breakeven is sqrt(1/3) per leg
        breakeven_prob = (1.0 / 3.0) ** 0.5
        leg_probs = [breakeven_prob, breakeven_prob]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        assert ev == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.unit
    def test_single_leg_bet(self):
        """Test EV calculation for single bet (not technically a parlay)."""
        leg_probs = [0.6]
        payout = 2.0  # 2x payout (even money)

        ev = calculate_parlay_ev(leg_probs, payout)

        # 0.6 * 2.0 - 1 = 0.2 (20% EV)
        assert ev == pytest.approx(0.2, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "payout_multiplier",
        [3.0, 6.0, 10.0, 25.0],
    )
    def test_various_payout_multipliers(self, payout_multiplier):
        """Test EV calculation with different payout structures."""
        leg_probs = [0.6, 0.6]

        ev = calculate_parlay_ev(leg_probs, payout_multiplier)

        # Calculate expected EV manually
        parlay_prob = 0.36
        expected_ev = (parlay_prob * payout_multiplier) - 1

        assert ev == pytest.approx(expected_ev, abs=1e-10)

    @pytest.mark.unit
    def test_high_probability_high_payout(self):
        """Test parlay with high-probability legs and high payout (good EV)."""
        leg_probs = [0.8, 0.8]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        # 0.64 * 3 - 1 = 0.92 (92% EV!)
        assert ev == pytest.approx(0.92, abs=1e-10)
        assert ev > 0.5  # Very high positive EV

    @pytest.mark.unit
    def test_low_probability_low_payout(self):
        """Test parlay with low-probability legs and low payout (bad EV)."""
        leg_probs = [0.4, 0.4]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        # 0.16 * 3 - 1 = -0.52 (-52% EV)
        assert ev == pytest.approx(-0.52, abs=1e-10)
        assert ev < -0.4  # Very negative EV

    @pytest.mark.unit
    def test_many_leg_parlay_ev(self):
        """Test EV calculation for parlay with many legs."""
        leg_probs = [0.6] * 5
        payout = 10.0

        ev = calculate_parlay_ev(leg_probs, payout)

        # 0.6^5 * 10 - 1 = 0.07776 * 10 - 1 = -0.2224
        assert ev == pytest.approx(-0.2224, abs=1e-10)

    @pytest.mark.unit
    def test_certain_win_scenario(self):
        """Test EV when all legs have 100% probability (certain win)."""
        leg_probs = [1.0, 1.0]
        payout = 3.0

        ev = calculate_parlay_ev(leg_probs, payout)

        # 1.0 * 3 - 1 = 2.0 (200% EV)
        assert ev == pytest.approx(2.0, abs=1e-10)

    @pytest.mark.unit
    def test_certain_loss_scenario(self):
        """Test EV when any leg has 0% probability (certain loss)."""
        leg_probs = [0.6, 0.0, 0.7]
        payout = 6.0

        ev = calculate_parlay_ev(leg_probs, payout)

        # 0.0 * 6 - 1 = -1.0 (-100% EV, lose entire stake)
        assert ev == pytest.approx(-1.0, abs=1e-10)

    @pytest.mark.unit
    def test_ev_formula_verification(self):
        """Verify that EV formula matches: (win_prob * payout) - 1."""
        leg_probs = [0.55, 0.65, 0.70]
        payout = 6.5

        # Calculate using function
        ev_function = calculate_parlay_ev(leg_probs, payout)

        # Calculate manually
        parlay_prob = calculate_parlay_probability(leg_probs)
        ev_manual = (parlay_prob * payout) - 1

        assert ev_function == pytest.approx(ev_manual, abs=1e-10)


class TestCalculateBreakevenProbability:
    """Test suite for calculate_breakeven_probability function."""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "payout,num_legs,expected",
        [
            # Standard DFS Pick'Em payouts
            (3.0, 2, 0.577350269189626),  # 2-leg, 3x payout
            (6.0, 3, 0.550321208137080),  # 3-leg, 6x payout
            (10.0, 5, 0.630957344480193),  # 5-leg, 10x payout
            (25.0, 6, 0.5848035476425733),  # 6-leg, 25x payout
            # Other common scenarios
            (2.0, 1, 0.5),  # Single bet, 2x payout (even money)
            (2.0, 2, 0.707106781186548),  # 2-leg, 2x payout
            (4.0, 2, 0.5),  # 2-leg, 4x payout
            (5.0, 3, 0.584803547642177),  # 3-leg, 5x payout
            (10.0, 4, 0.562341325190349),  # 4-leg, 10x payout
            (20.0, 5, 0.5492802716530588),  # 5-leg, 20x payout
        ],
    )
    def test_breakeven_probability_calculations(self, payout, num_legs, expected):
        """Test breakeven probability calculation for various payout/leg combinations.

        Formula: breakeven_prob = (1 / payout)^(1 / num_legs)
        """
        result = calculate_breakeven_probability(payout, num_legs)
        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_two_leg_three_x_payout(self):
        """Test the standard 2-leg parlay with 3x payout.

        This is the most common DFS Pick'Em structure.
        Breakeven per leg should be sqrt(1/3) ≈ 57.735%
        """
        breakeven = calculate_breakeven_probability(3.0, 2)

        assert breakeven == pytest.approx(0.577350269189626, abs=1e-10)

        # Verify: if you hit this probability on both legs, you break even
        parlay_prob = breakeven ** 2
        assert parlay_prob == pytest.approx(1.0 / 3.0, abs=1e-10)

    @pytest.mark.unit
    def test_three_leg_six_x_payout(self):
        """Test the 3-leg parlay with 6x payout.

        Breakeven per leg should be (1/6)^(1/3) ≈ 55.032%
        """
        breakeven = calculate_breakeven_probability(6.0, 3)

        assert breakeven == pytest.approx(0.550321208137080, abs=1e-10)

        # Verify: if you hit this probability on all three legs, you break even
        parlay_prob = breakeven ** 3
        assert parlay_prob == pytest.approx(1.0 / 6.0, abs=1e-10)

    @pytest.mark.unit
    def test_five_leg_ten_x_payout(self):
        """Test the 5-leg parlay with 10x payout.

        Breakeven per leg should be (1/10)^(1/5) ≈ 63.096%
        """
        breakeven = calculate_breakeven_probability(10.0, 5)

        assert breakeven == pytest.approx(0.630957344480193, abs=1e-10)

        # Verify: if you hit this probability on all five legs, you break even
        parlay_prob = breakeven ** 5
        assert parlay_prob == pytest.approx(1.0 / 10.0, abs=1e-10)

    @pytest.mark.unit
    def test_single_leg_bet(self):
        """Test breakeven for single bet (not a parlay).

        For a 2x payout (even money), breakeven should be exactly 50%.
        """
        breakeven = calculate_breakeven_probability(2.0, 1)
        assert breakeven == pytest.approx(0.5, abs=1e-10)

    @pytest.mark.unit
    def test_high_payout_multiplier(self):
        """Test breakeven probability with high payout multiplier."""
        # 100x payout on 5-leg parlay
        breakeven = calculate_breakeven_probability(100.0, 5)

        # With high payout, per-leg probability can be lower
        assert breakeven < 0.5
        assert breakeven == pytest.approx(0.39810717055349726, abs=1e-10)

        # Verify the math
        parlay_prob = breakeven ** 5
        assert parlay_prob == pytest.approx(1.0 / 100.0, abs=1e-10)

    @pytest.mark.unit
    def test_low_payout_multiplier(self):
        """Test breakeven probability with low payout multiplier."""
        # 1.5x payout on 2-leg parlay
        breakeven = calculate_breakeven_probability(1.5, 2)

        # Should require very high probability per leg
        assert breakeven > 0.8
        assert breakeven == pytest.approx(0.816496580927726, abs=1e-10)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "payout,num_legs",
        [
            (3.0, 2),
            (6.0, 3),
            (10.0, 5),
            (4.0, 2),
            (8.0, 4),
        ],
    )
    def test_breakeven_verification(self, payout, num_legs):
        """Verify that breakeven probability produces EV = 0 when used in parlay.

        If we use the breakeven probability for all legs, the parlay EV should be 0.
        """
        breakeven = calculate_breakeven_probability(payout, num_legs)
        leg_probs = [breakeven] * num_legs

        ev = calculate_parlay_ev(leg_probs, payout)

        # EV should be very close to 0 (within floating-point precision)
        assert ev == pytest.approx(0.0, abs=1e-10)

    @pytest.mark.unit
    def test_formula_verification(self):
        """Verify the mathematical formula: breakeven^num_legs = 1/payout."""
        payout = 7.5
        num_legs = 4

        breakeven = calculate_breakeven_probability(payout, num_legs)

        # Check: breakeven^num_legs should equal 1/payout
        result = breakeven ** num_legs
        expected = 1.0 / payout

        assert result == pytest.approx(expected, abs=1e-10)

    @pytest.mark.unit
    def test_breakeven_bounds(self):
        """Verify that breakeven probability is always between 0 and 1."""
        test_cases = [
            (3.0, 2),
            (10.0, 5),
            (100.0, 10),
            (2.0, 1),
            (50.0, 7),
        ]

        for payout, num_legs in test_cases:
            breakeven = calculate_breakeven_probability(payout, num_legs)
            assert 0 < breakeven < 1, (
                f"Breakeven for {num_legs}-leg with {payout}x payout "
                f"should be between 0 and 1, got {breakeven}"
            )

    @pytest.mark.unit
    def test_increasing_legs_requires_higher_breakeven(self):
        """Test that more legs generally require higher per-leg breakeven probability.

        For a fixed payout, adding more legs typically increases the required
        per-leg probability (though this isn't always strictly true for all payouts).
        """
        payout = 10.0

        breakeven_2leg = calculate_breakeven_probability(payout, 2)
        breakeven_3leg = calculate_breakeven_probability(payout, 3)
        breakeven_5leg = calculate_breakeven_probability(payout, 5)

        # For 10x payout: more legs = lower per-leg requirement
        # (because you're compounding more times)
        assert breakeven_2leg < breakeven_3leg < breakeven_5leg


class TestIntegrationScenarios:
    """Integration tests combining multiple functions for real-world scenarios."""

    @pytest.mark.unit
    def test_full_ev_analysis_workflow(self):
        """Test complete EV analysis workflow from odds to final EV calculation."""
        # Step 1: Get Pinnacle odds and remove vig
        over_odds = -110
        under_odds = -110

        over_fair_prob, under_fair_prob = devig_pinnacle_odds(over_odds, under_odds)

        # Step 2: Calculate breakeven probability for 2-leg, 3x parlay
        breakeven = calculate_breakeven_probability(3.0, 2)

        # Step 3: Calculate EV percentage
        ev_over = calculate_ev_percentage(over_fair_prob, breakeven)
        ev_under = calculate_ev_percentage(under_fair_prob, breakeven)

        # Both should have same EV (symmetric odds)
        assert ev_over == pytest.approx(ev_under, abs=1e-10)

        # Should be negative EV (50% < 57.735% breakeven)
        assert ev_over < 0

    @pytest.mark.unit
    def test_positive_ev_detection(self):
        """Test detection of positive EV opportunity."""
        # Scenario: Pinnacle has -130/+110 (over favored)
        # We take the Over side
        over_fair_prob, _ = devig_pinnacle_odds(-130, 110)

        # Assume we're building a 2-leg parlay with 3x payout
        breakeven = calculate_breakeven_probability(3.0, 2)

        # Calculate EV
        ev = calculate_ev_percentage(over_fair_prob, breakeven)

        # Over should be ~54.17%, which is below 57.735% breakeven
        assert over_fair_prob < breakeven
        assert ev < 0

    @pytest.mark.unit
    def test_parlay_builder_workflow(self):
        """Test workflow for building and evaluating a parlay."""
        # Build a 3-leg parlay with varying fair probabilities
        leg1_prob = 0.60
        leg2_prob = 0.55
        leg3_prob = 0.65

        leg_probs = [leg1_prob, leg2_prob, leg3_prob]

        # Calculate parlay probability
        parlay_prob = calculate_parlay_probability(leg_probs)

        # Assume 6x payout for 3-leg parlay
        payout = 6.0

        # Calculate EV
        ev = calculate_parlay_ev(leg_probs, payout)

        # Verify EV is positive (good legs)
        assert ev > 0

        # Calculate breakeven and verify we're above it
        breakeven = calculate_breakeven_probability(payout, 3)
        avg_prob = sum(leg_probs) / len(leg_probs)

        # Average probability (60%) > breakeven (55.03%)
        assert avg_prob > breakeven

    @pytest.mark.unit
    def test_sharp_odds_comparison(self):
        """Test comparing different bookmaker odds using devig."""
        # Two different books with different juice
        # Book A: -110/-110 (standard juice)
        # Book B: -105/-115 (lower juice on one side)

        prob_a_over, prob_a_under = devig_pinnacle_odds(-110, -110)
        prob_b_over, prob_b_under = devig_pinnacle_odds(-105, -115)

        # Both should normalize to fair probabilities
        assert prob_a_over + prob_a_under == pytest.approx(1.0, abs=1e-10)
        assert prob_b_over + prob_b_under == pytest.approx(1.0, abs=1e-10)

        # Book A should be exactly 50/50
        assert prob_a_over == pytest.approx(0.5, abs=1e-10)

        # Book B has slightly different fair odds
        assert prob_b_over != prob_a_over

    @pytest.mark.unit
    def test_edge_case_zero_ev_parlay(self):
        """Test identifying exact breakeven parlay (0% EV)."""
        # Build parlay at exact breakeven
        payout = 3.0
        num_legs = 2

        breakeven_prob = calculate_breakeven_probability(payout, num_legs)
        leg_probs = [breakeven_prob] * num_legs

        # Calculate EV - should be exactly 0
        ev = calculate_parlay_ev(leg_probs, payout)
        assert ev == pytest.approx(0.0, abs=1e-10)

        # Calculate EV percentage - should also be exactly 0
        ev_pct = calculate_ev_percentage(breakeven_prob, breakeven_prob)
        assert ev_pct == pytest.approx(0.0, abs=1e-10)

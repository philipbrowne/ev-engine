"""Math logic and EV calculation for sports betting analysis.

This module provides pure mathematical functions for analyzing betting opportunities,
including probability calculations, vig removal, and expected value computations.
All functions are stateless and have no dependencies on APIs or databases.
"""

from typing import Tuple


def calculate_implied_probability(american_odds: int) -> float:
    """Convert American odds to implied probability.

    American odds can be positive (underdog) or negative (favorite).
    - Positive odds (e.g., +150): represents profit on $100 bet
    - Negative odds (e.g., -150): represents amount needed to bet to win $100

    Args:
        american_odds: American format odds (e.g., -110, +150)

    Returns:
        Implied probability as a decimal between 0 and 1

    Examples:
        >>> calculate_implied_probability(-110)  # Slight favorite
        0.5238095238095238
        >>> calculate_implied_probability(100)  # Even odds
        0.5
        >>> calculate_implied_probability(150)  # Underdog
        0.4
    """
    if american_odds > 0:
        # For positive odds: probability = 100 / (odds + 100)
        return 100 / (american_odds + 100)
    else:
        # For negative odds: probability = |odds| / (|odds| + 100)
        return abs(american_odds) / (abs(american_odds) + 100)


def devig_pinnacle_odds(over_odds: int, under_odds: int) -> Tuple[float, float]:
    """Remove vig from Pinnacle odds to find fair probabilities.

    Uses the multiplicative/proportional method to remove the vigorish (bookmaker's edge)
    from a two-sided market. This method assumes the vig is distributed proportionally
    across both sides of the market.

    The process:
    1. Convert American odds to implied probabilities
    2. Sum the implied probabilities (will be > 1.0 due to vig)
    3. Normalize each probability by dividing by the sum (removes vig)

    Args:
        over_odds: American odds for the Over side
        under_odds: American odds for the Under side

    Returns:
        Tuple of (fair_over_probability, fair_under_probability)
        Both values are decimals between 0 and 1, and sum to exactly 1.0

    Examples:
        >>> devig_pinnacle_odds(-110, -110)  # Standard -110/-110 line
        (0.5, 0.5)
        >>> over_prob, under_prob = devig_pinnacle_odds(-130, 110)
        >>> over_prob  # doctest: +ELLIPSIS
        0.566...
        >>> under_prob  # doctest: +ELLIPSIS
        0.433...
        >>> abs(over_prob + under_prob - 1.0) < 0.0001  # Probabilities sum to 1
        True
    """
    # Convert American odds to implied probabilities
    over_implied = calculate_implied_probability(over_odds)
    under_implied = calculate_implied_probability(under_odds)

    # The sum of implied probabilities includes the vig
    total_implied = over_implied + under_implied

    # Remove vig by normalizing (dividing each by the sum)
    fair_over_prob = over_implied / total_implied
    fair_under_prob = under_implied / total_implied

    return fair_over_prob, fair_under_prob


def calculate_ev_percentage(
    fair_prob: float,
    implied_breakeven_prob: float,
    parlay_legs: int = 1,
) -> float:
    """Calculate EV percentage for a given fair probability vs breakeven probability.

    Expected Value (EV) represents the theoretical average profit or loss per bet
    if the bet were repeated infinitely. Positive EV indicates a profitable bet
    over the long run.

    For DFS Pick-Em style bets:
    - 2-leg parlay pays 3x (implied breakeven per leg = sqrt(1/3) ≈ 57.7%)
    - 3-leg parlay pays 6x (implied breakeven per leg = (1/6)^(1/3) ≈ 55.0%)
    - 5-leg parlay pays 10x (implied breakeven per leg = (1/10)^(1/5) ≈ 54.25%)

    The EV% formula compares the fair probability to the breakeven probability:
    EV% = ((fair_prob / breakeven_prob) - 1) * 100

    Args:
        fair_prob: Fair win probability for this leg (0 to 1), typically from devigged
            sharp bookmaker odds
        implied_breakeven_prob: Required win probability per leg to break even on the
            parlay structure (e.g., 0.5425 for 5-leg 10x parlay)
        parlay_legs: Number of legs in the parlay (default: 1 for single bets)

    Returns:
        Expected value as a percentage (e.g., 5.0 means +5% EV)
        Positive values indicate +EV (profitable), negative values indicate -EV (unprofitable)

    Examples:
        >>> calculate_ev_percentage(0.60, 0.5425)  # Good edge
        10.599...
        >>> calculate_ev_percentage(0.54, 0.5425)  # Slight edge
        -0.460...
        >>> calculate_ev_percentage(0.50, 0.5425)  # Negative EV
        -7.834...
    """
    # EV% = ((fair_prob / breakeven_prob) - 1) * 100
    # This represents how much our fair probability exceeds the breakeven threshold
    ev_percentage = ((fair_prob / implied_breakeven_prob) - 1) * 100

    return ev_percentage


def calculate_parlay_probability(leg_probabilities: list[float]) -> float:
    """Calculate the combined win probability for a parlay bet.

    For independent events, the parlay win probability is the product of all
    individual leg probabilities.

    Args:
        leg_probabilities: List of individual leg win probabilities (each 0 to 1)

    Returns:
        Combined parlay win probability (0 to 1)

    Examples:
        >>> calculate_parlay_probability([0.6, 0.6])  # 2-leg parlay
        0.36
        >>> calculate_parlay_probability([0.577, 0.577])  # Break-even 2-leg for 3x
        0.332929
        >>> calculate_parlay_probability([0.5, 0.5, 0.5])  # 3-leg 50/50
        0.125
    """
    parlay_prob = 1.0
    for prob in leg_probabilities:
        parlay_prob *= prob
    return parlay_prob


def calculate_parlay_ev(
    leg_probabilities: list[float],
    payout_multiplier: float,
) -> float:
    """Calculate expected value for a parlay bet.

    EV represents the theoretical profit/loss per unit wagered over infinite trials.

    Formula: EV = (Parlay_Win_Probability * Payout_Multiplier) - 1

    The "-1" accounts for the initial stake. For example, a 3x payout means you get
    3 units back (2 units profit + 1 unit stake), so the profit is (3 * prob) - 1.

    Args:
        leg_probabilities: List of individual leg win probabilities (each 0 to 1)
        payout_multiplier: Total payout multiplier (e.g., 3.0 for a 2-leg DFS parlay)

    Returns:
        Expected value as a decimal (e.g., 0.05 means +5% EV, or +$0.05 per $1 wagered)
        Positive values indicate +EV, negative values indicate -EV

    Examples:
        >>> calculate_parlay_ev([0.6, 0.6], 3.0)  # 60% legs, 3x payout
        0.08
        >>> calculate_parlay_ev([0.577, 0.577], 3.0)  # Break-even
        -0.001213...
        >>> calculate_parlay_ev([0.5, 0.5], 3.0)  # 50% legs, -EV
        -0.25
    """
    parlay_prob = calculate_parlay_probability(leg_probabilities)
    ev = (parlay_prob * payout_multiplier) - 1
    return ev


def calculate_breakeven_probability(payout_multiplier: float, num_legs: int) -> float:
    """Calculate the required per-leg win probability to break even on a parlay.

    For a parlay to break even (EV = 0), the combined win probability must equal
    1 / payout_multiplier. Since parlay probability = (leg_prob)^num_legs, we need:
    (leg_prob)^num_legs = 1 / payout_multiplier
    Therefore: leg_prob = (1 / payout_multiplier)^(1 / num_legs)

    Args:
        payout_multiplier: Total payout multiplier (e.g., 3.0, 6.0, 10.0)
        num_legs: Number of independent legs in the parlay

    Returns:
        Required win probability per leg to break even (0 to 1)

    Examples:
        >>> calculate_breakeven_probability(3.0, 2)  # 2-leg, 3x payout
        0.577350...
        >>> calculate_breakeven_probability(10.0, 5)  # 5-leg, 10x payout
        0.630957...
        >>> calculate_breakeven_probability(6.0, 3)  # 3-leg, 6x payout
        0.550321...
    """
    return (1 / payout_multiplier) ** (1 / num_legs)

"""Rule-based trading strategies."""

from trading_bot.ml.rules.momentum import (
    RSIOversoldRule,
    RSIOverboughtShortRule,
    MACDBullishCrossRule,
    MACDTrendRule,
    MomentumVolumeRule,
)
from trading_bot.ml.rules.mean_reversion import (
    BollingerBounceRule,
    BollingerBreakoutRule,
    SMADeviationRule,
    ZScoreReversionRule,
    DonchianChannelBreakoutRule,
)
from trading_bot.ml.rules.volatility import (
    ATRExpansionRule,
    LowVolatilityBreakoutRule,
    KeltnerChannelRule,
    ADXTrendStrengthRule,
    VolatilitySqueezeRule,
)

# Registry of all available rules (15 total)
ALL_RULES = [
    # Momentum strategies (5)
    RSIOversoldRule,
    RSIOverboughtShortRule,
    MACDBullishCrossRule,
    MACDTrendRule,
    MomentumVolumeRule,
    # Mean reversion strategies (5)
    BollingerBounceRule,
    BollingerBreakoutRule,
    SMADeviationRule,
    ZScoreReversionRule,
    DonchianChannelBreakoutRule,
    # Volatility strategies (5)
    ATRExpansionRule,
    LowVolatilityBreakoutRule,
    KeltnerChannelRule,
    ADXTrendStrengthRule,
    VolatilitySqueezeRule,
]

__all__ = [
    "ALL_RULES",
    # Momentum
    "RSIOversoldRule",
    "RSIOverboughtShortRule",
    "MACDBullishCrossRule",
    "MACDTrendRule",
    "MomentumVolumeRule",
    # Mean Reversion
    "BollingerBounceRule",
    "BollingerBreakoutRule",
    "SMADeviationRule",
    "ZScoreReversionRule",
    "DonchianChannelBreakoutRule",
    # Volatility
    "ATRExpansionRule",
    "LowVolatilityBreakoutRule",
    "KeltnerChannelRule",
    "ADXTrendStrengthRule",
    "VolatilitySqueezeRule",
]

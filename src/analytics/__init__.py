"""
Analytics Package
Advanced blockchain analytics modules for GLQ Chain.
"""

from .token_analytics import TokenAnalytics, TokenTransfer, TokenInfo
from .dex_analytics import DEXAnalytics, SwapEvent, LiquidityEvent, TradingPair
from .defi_analytics import DeFiAnalytics, LendingEvent, StakingEvent, YieldEvent, ProtocolMetrics
from .advanced_analytics import AdvancedAnalytics, add_analytics_to_processor

__all__ = [
    'TokenAnalytics', 'TokenTransfer', 'TokenInfo',
    'DEXAnalytics', 'SwapEvent', 'LiquidityEvent', 'TradingPair',
    'DeFiAnalytics', 'LendingEvent', 'StakingEvent', 'YieldEvent', 'ProtocolMetrics',
    'AdvancedAnalytics', 'add_analytics_to_processor'
]

__version__ = "1.0.0"
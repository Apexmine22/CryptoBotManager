"""
Ядро приложения Crypto Bot Manager
"""

from .base_bot import BaseBot, BotStatus, BotStats
from .browser_manager import BrowserManager
from .captcha_solver import CaptchaSolver
from .bot_manager import BotManager
from .config_manager import (
    ConfigManager,
    UniversalBotConfig,
    BrowserConfig,
    CaptchaConfig,
    BotSelectorConfig,
    BotNavigationConfig,
    BotSettingsConfig,
    CaptchaSettingsConfig,
)
from .template_bot import TemplateBot
from .universal_bot import UniversalBot

__all__ = [
    "BaseBot",
    "BotStatus",
    "BotStats",
    "BrowserManager",
    "CaptchaSolver",
    "BotManager",
    "ConfigManager",
    "TemplateBot",
    "UniversalBot",
    "UniversalBotConfig",
    "BrowserConfig",
    "CaptchaConfig",
    "BotSelectorConfig",
    "BotNavigationConfig",
    "BotSettingsConfig",
    "CaptchaSettingsConfig",
]

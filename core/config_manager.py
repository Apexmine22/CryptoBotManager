# core/config_manager.py
"""
Менеджер конфигурации v3.0 – поддержка шаблонов
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logger import logger


@dataclass
class BrowserConfig:
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = ""
    timeout: int = 30000
    navigation_timeout: int = 60000
    disable_javascript: bool = False
    block_resources: bool = True
    disable_css: bool = False


@dataclass
class CaptchaConfig:
    service_url: str = "http://api.multibot.in"
    api_key: str = ""
    timeout: int = 120
    sleep: int = 5
    verify_ssl: bool = False


@dataclass
class BotSelectorConfig:
    email_field: str = ""
    password_field: str = ""
    login_button: str = ""
    login_link: str = ""
    claim_button: str = ""
    roll_button: str = ""
    captcha_frame: str = ""
    balance_text: str = ""
    faucet_button: str = ""
    timer_text: str = ""
    username_field: str = ""
    success_indicator: str = ""
    error_indicator: str = ""


@dataclass
class BotNavigationConfig:
    login_url: str = ""
    dashboard_url: str = ""
    claim_url: str = ""
    faucet_url: str = ""
    profile_url: str = ""
    balance_url: str = ""


@dataclass
class BotSettingsConfig:
    wait_timeout: int = 30
    max_retries: int = 3
    screenshot_on_error: bool = True
    save_cookies: bool = True
    enable_proxy: bool = False
    proxy_url: str = ""
    random_delays: bool = True
    min_delay: int = 2
    max_delay: int = 5


@dataclass
class CaptchaSettingsConfig:
    captcha_type: str = "auto"
    site_key: str = ""
    page_url: str = ""
    image_selector: str = ""
    captcha_frame: str = ""
    auto_solve: bool = True
    retry_on_fail: bool = True


@dataclass
class UniversalBotConfig:
    """Универсальная конфигурация бота с поддержкой шаблонов"""
    name: str
    enabled: bool
    url: str
    email: str
    password: str

    # Новое поле для указания шаблона
    template: str = ""

    cycle_delay: int = 300
    currency_delay: int = 3
    max_consecutive_errors: int = 5
    stop_on_critical_error: bool = True

    login_selectors: BotSelectorConfig = field(default_factory=BotSelectorConfig)
    action_selectors: BotSelectorConfig = field(default_factory=BotSelectorConfig)
    navigation: BotNavigationConfig = field(default_factory=BotNavigationConfig)
    settings: BotSettingsConfig = field(default_factory=BotSettingsConfig)
    captcha: CaptchaSettingsConfig = field(default_factory=CaptchaSettingsConfig)

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "3.0"


class ConfigManager:
    def __init__(self,
                 config_path: str = "config.yaml",
                 bot_config_path: str = "bot_config.yaml"):
        self.config_path = Path(config_path)
        self.bot_config_path = Path(bot_config_path)
        self.data: Dict[str, Any] = {}
        self.bot_data: Dict[str, Any] = {}

        self.load_config()
        self.load_bot_config()
        self._ensure_templates()

    def _ensure_templates(self):
        """Создание папки templates и примеров шаблонов"""
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)

        # Создание примера шаблона, если его нет
        example_template = templates_dir / "example.py"
        if not example_template.exists():
            self._create_example_template()

    def _create_example_template(self):
        """Создание примера шаблона"""
        example_code = '''"""
Пример шаблона бота
"""
import asyncio
from playwright.async_api import Page

from core.base_bot import BaseBot, BotStatus
from core.config_manager import UniversalBotConfig
from utils.logger import logger


async def login(page: Page, config: UniversalBotConfig, bot: BaseBot) -> bool:
    """Пример функции логина"""
    try:
        bot.update_status(BotStatus.LOGGING_IN, "Пример логина")

        await page.goto(config.url)
        await asyncio.sleep(2)

        # Ваша логика авторизации здесь
        logger.info(f"Выполняется логин для {config.name}")

        return True
    except Exception as e:
        logger.error(f"Ошибка логина: {e}")
        return False


async def perform_actions(page: Page, config: UniversalBotConfig, bot: BaseBot) -> bool:
    """Пример функции выполнения действий"""
    try:
        bot.update_status(BotStatus.WORKING, "Пример действий")

        # Ваша логика действий здесь
        logger.info(f"Выполняются действия для {config.name}")

        return True
    except Exception as e:
        logger.error(f"Ошибка действий: {e}")
        return False


async def is_logged_in(page: Page, config: UniversalBotConfig, bot: BaseBot) -> bool:
    """Пример проверки авторизации"""
    try:
        # Ваша логика проверки здесь
        return True
    except Exception:
        return False
'''
        with open(Path("templates") / "example.py", "w", encoding="utf-8") as f:
            f.write(example_code)

        logger.info("Создан пример шаблона: templates/example.py")

    def load_config(self):
        if not self.config_path.exists():
            self.create_default_config()
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
            logger.info("Основная конфигурация загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            self.create_default_config()

    def create_default_config(self):
        default_config = {
            "version": "3.0",
            "browser": {
                "headless": True,
                "viewport_width": 1920,
                "viewport_height": 1080,
                "user_agent": "",
                "timeout": 30000,
                "navigation_timeout": 60000,
                "disable_javascript": False,
                "block_resources": True,
                "disable_css": False,
            },
            "captcha": {
                "service_url": "http://api.multibot.in",
                "api_key": "your_api_key_here",
                "timeout": 120,
                "sleep": 5,
                "verify_ssl": False,
            },
            "proxy": {
                "enable_proxy": False,
                "proxy_url": "",
                "proxy_type": "HTTP",
                "rotation_enabled": False,
                "rotation_interval": 10,
                "proxy_list": [],
            },
            "general": {
                "auto_start": False,
                "minimize_to_tray": False,
                "auto_update": True,
                "ui_update_interval": 2000,
            },
            "logging": {
                "level": "INFO",
                "save_to_file": True,
                "max_size_mb": 100,
            }
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False,
                      allow_unicode=True, indent=2)
        self.data = default_config
        logger.info("Создана конфигурация по умолчанию")

    def load_bot_config(self):
        if not self.bot_config_path.exists():
            self.create_default_bot_config()
            return
        try:
            with open(self.bot_config_path, "r", encoding="utf-8") as f:
                self.bot_data = yaml.safe_load(f) or {}
            logger.info("Конфигурация ботов загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки bot_config.yaml: {e}")
            self.create_default_bot_config()

    def create_default_bot_config(self):
        default_bot_config = {
            "version": "3.0",
            "bots": {},
        }
        self.bot_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.bot_config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_bot_config, f, default_flow_style=False,
                      allow_unicode=True, indent=2)
        self.bot_data = default_bot_config
        logger.info("Создана пустая конфигурация ботов")

    def get_browser_config(self) -> BrowserConfig:
        browser_data = self.data.get("browser", {})
        return BrowserConfig(**browser_data)

    def get_captcha_config(self) -> CaptchaConfig:
        captcha_data = self.data.get("captcha", {})
        return CaptchaConfig(**captcha_data)

    def get_universal_bot_configs(self) -> List[UniversalBotConfig]:
        bots_cfg: List[UniversalBotConfig] = []
        bots_dict = self.bot_data.get("bots", {})

        for bot_key, bot_cfg in bots_dict.items():
            try:
                # Обеспечиваем обратную совместимость
                if not isinstance(bot_cfg, dict):
                    continue

                login_sel = BotSelectorConfig(**bot_cfg.get("login_selectors", {}))
                action_sel = BotSelectorConfig(**bot_cfg.get("action_selectors", {}))
                navigation = BotNavigationConfig(**bot_cfg.get("navigation", {}))
                settings = BotSettingsConfig(**bot_cfg.get("settings", {}))
                captcha = CaptchaSettingsConfig(**bot_cfg.get("captcha", {}))

                bot = UniversalBotConfig(
                    name=bot_cfg.get("name", bot_key),
                    enabled=bot_cfg.get("enabled", False),
                    url=bot_cfg.get("url", ""),
                    email=bot_cfg.get("email", ""),
                    password=bot_cfg.get("password", ""),
                    template=bot_cfg.get("template", ""),  # Новое поле
                    cycle_delay=bot_cfg.get("cycle_delay", 300),
                    currency_delay=bot_cfg.get("currency_delay", 3),
                    max_consecutive_errors=bot_cfg.get("max_consecutive_errors", 5),
                    stop_on_critical_error=bot_cfg.get("stop_on_critical_error", True),
                    login_selectors=login_sel,
                    action_selectors=action_sel,
                    navigation=navigation,
                    settings=settings,
                    captcha=captcha,
                )
                bots_cfg.append(bot)
            except Exception as e:
                logger.error(f"Ошибка загрузки конфигурации бота {bot_key}: {e}")
                continue
        return bots_cfg

    def save_bot_config(self):
        try:
            with open(self.bot_config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.bot_data, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
            logger.info("Конфигурация ботов сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации ботов: {e}")

    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.data, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
            logger.info("Основная конфигурация сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения основной конфигурации: {e}")

    def get_wallets(self) -> Dict[str, str]:
        return self.bot_data.get("wallets", {})

    def set_wallets(self, wallets: Dict[str, str]) -> None:
        self.bot_data["wallets"] = wallets
        self.save_bot_config()

    def get_available_templates(self) -> List[str]:
        """Получение списка доступных шаблонов"""
        templates_dir = Path("templates")
        if not templates_dir.exists():
            return []

        templates = []
        for f in templates_dir.glob("*.py"):
            if f.is_file() and f.name != "__init__.py":
                templates.append(f.stem)
        return sorted(templates)

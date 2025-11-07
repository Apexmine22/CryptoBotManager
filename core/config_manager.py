# core/config_manager.py
"""
Менеджер конфигурации v4.1 - исправленная версия
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
    timeout: int = 30000
    navigation_timeout: int = 60000
    user_agent: str = ""
    disable_javascript: bool = False
    block_resources: bool = True
    proxy_server: str = ""


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
    block_resources: bool = True  # Добавлен отсутствующий атрибут
    disable_javascript: bool = False  # Добавлен для совместимости


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
    version: str = "4.1"


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
        self._ensure_directories()

    def _ensure_directories(self):
        """Создание необходимых директорий"""
        directories = [
            "data/cookies",
            "data/screenshots",
            "data/logs",
            "templates",
            "logs"
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def load_config(self):
        """Загрузка основной конфигурации"""
        if not self.config_path.exists():
            self.create_default_config()
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
            logger.info("✅ Основная конфигурация загружена")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            self.create_default_config()

    def create_default_config(self):
        """Создание конфигурации по умолчанию"""
        default_config = {
            "version": "4.1",
            "browser": {
                "headless": True,
                "viewport_width": 1920,
                "viewport_height": 1080,
                "user_agent": "",
                "timeout": 30000,
                "navigation_timeout": 60000,
                "disable_javascript": False,
                "block_resources": True,
            },
            "captcha": {
                "service_url": "http://api.multibot.in",
                "api_key": "",
                "timeout": 120,
                "sleep": 5,
                "verify_ssl": False,
            },
            "general": {
                "auto_start": False,
                "default_email": "",
                "default_password": "",
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False,
                      allow_unicode=True, indent=2)
        self.data = default_config
        logger.info("✅ Создана конфигурация по умолчанию")

    def load_bot_config(self):
        """Загрузка конфигурации ботов"""
        if not self.bot_config_path.exists():
            self.create_default_bot_config()
        try:
            with open(self.bot_config_path, "r", encoding="utf-8") as f:
                self.bot_data = yaml.safe_load(f) or {}
            logger.info("✅ Конфигурация ботов загружена")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки bot_config.yaml: {e}")
            self.create_default_bot_config()

    def create_default_bot_config(self):
        """Создание конфигурации ботов по умолчанию"""
        default_bot_config = {
            "version": "4.1",
            "bots": {},
        }

        self.bot_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.bot_config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_bot_config, f, default_flow_style=False,
                      allow_unicode=True, indent=2)
        self.bot_data = default_bot_config
        logger.info("✅ Создана конфигурация ботов по умолчанию")

    def get_browser_config(self) -> BrowserConfig:
        """Получение конфигурации браузера"""
        browser_data = self.data.get('browser', {})
        return BrowserConfig(**browser_data)

    def get_captcha_config(self) -> CaptchaConfig:
        """Получение конфигурации капчи"""
        captcha_data = self.data.get("captcha", {})
        return CaptchaConfig(**captcha_data)

    def get_universal_bot_configs(self) -> List[UniversalBotConfig]:
        """Получение конфигураций всех ботов"""
        bots_cfg = []
        bots_dict = self.bot_data.get("bots", {})

        for bot_key, bot_data in bots_dict.items():
            try:
                if not isinstance(bot_data, dict):
                    continue

                # Создаем объекты конфигурации
                login_selectors = BotSelectorConfig(**bot_data.get("login_selectors", {}))
                action_selectors = BotSelectorConfig(**bot_data.get("action_selectors", {}))
                navigation = BotNavigationConfig(**bot_data.get("navigation", {}))
                settings = BotSettingsConfig(**bot_data.get("settings", {}))
                captcha = CaptchaSettingsConfig(**bot_data.get("captcha", {}))

                bot_config = UniversalBotConfig(
                    name=bot_data.get("name", bot_key),
                    enabled=bot_data.get("enabled", False),
                    url=bot_data.get("url", ""),
                    email=bot_data.get("email", ""),
                    password=bot_data.get("password", ""),
                    template=bot_data.get("template", ""),
                    cycle_delay=bot_data.get("cycle_delay", 300),
                    currency_delay=bot_data.get("currency_delay", 3),
                    max_consecutive_errors=bot_data.get("max_consecutive_errors", 5),
                    stop_on_critical_error=bot_data.get("stop_on_critical_error", True),
                    login_selectors=login_selectors,
                    action_selectors=action_selectors,
                    navigation=navigation,
                    settings=settings,
                    captcha=captcha,
                )
                bots_cfg.append(bot_config)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки конфигурации бота {bot_key}: {e}")
                continue

        return bots_cfg

    def save_bot_config(self):
        """Сохранение конфигурации ботов"""
        try:
            with open(self.bot_config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.bot_data, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
            logger.info("✅ Конфигурация ботов сохранена")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения конфигурации ботов: {e}")

    def save_config(self):
        """Сохранение основной конфигурации"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.data, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
            logger.info("✅ Основная конфигурация сохранена")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения основной конфигурации: {e}")

    def get_available_templates(self) -> List[str]:
        """Получение списка доступных шаблонов"""
        templates_dir = Path("templates")
        if not templates_dir.exists():
            return []
        return sorted([f.stem for f in templates_dir.glob("*.py")
                       if f.is_file() and f.name != "__init__.py"])
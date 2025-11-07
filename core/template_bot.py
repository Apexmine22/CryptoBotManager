# core/template_bot.py
"""
Бот на основе шаблонов - современная архитектура
"""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from .base_bot import BaseBot, BotStatus
from .config_manager import UniversalBotConfig
from utils.logger import logger


class TemplateBot(BaseBot):
    """Бот, загружающий логику из шаблонов в папке templates"""

    def __init__(self, config: UniversalBotConfig, config_manager):
        super().__init__(config, config_manager)
        self.template_module = None
        self.template_name = getattr(config, 'template', 'default')
        self._load_template()

    def _load_template(self):
        """Загрузка шаблона из папки templates"""
        try:
            templates_dir = Path("templates")
            template_file = templates_dir / f"{self.template_name}.py"

            if not template_file.exists():
                logger.error(f"Шаблон {self.template_name} не найден")
                return False

            # Динамическая загрузка модуля
            spec = importlib.util.spec_from_file_location(
                f"template_{self.template_name}",
                template_file
            )
            self.template_module = importlib.util.module_from_spec(spec)
            sys.modules[f"template_{self.template_name}"] = self.template_module
            spec.loader.exec_module(self.template_module)

            logger.success(f"Загружен шаблон: {self.template_name}")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки шаблона {self.template_name}: {e}")
            return False

    async def login(self, page) -> bool:
        """Логика авторизации из шаблона"""
        if not self.template_module or not hasattr(self.template_module, 'login'):
            logger.error(f"Шаблон {self.template_name} не содержит функцию login")
            return False

        try:
            self.update_status(BotStatus.LOGGING_IN, "Авторизация через шаблон")
            result = await self.template_module.login(page, self.config, self)

            if result:
                self.update_status(BotStatus.RUNNING, "Авторизация успешна")
                return True
            else:
                self.update_status(BotStatus.ERROR, "Ошибка авторизации")
                return False

        except Exception as e:
            self.update_status(BotStatus.ERROR, f"Ошибка авторизации: {e}")
            return False

    async def perform_actions(self, page) -> bool:
        """Основные действия из шаблона"""
        if not self.template_module or not hasattr(self.template_module, 'perform_actions'):
            logger.error(f"Шаблон {self.template_name} не содержит функцию perform_actions")
            return False

        try:
            self.update_status(BotStatus.WORKING, "Выполнение действий через шаблон")
            result = await self.template_module.perform_actions(page, self.config, self)

            if result:
                self.update_status(BotStatus.COLLECTING_REWARD, "Действия выполнены успешно")
                return True
            else:
                self.update_status(BotStatus.WAITING, "Действия завершены")
                return False

        except Exception as e:
            self.update_status(BotStatus.ERROR, f"Ошибка выполнения действий: {e}")
            return False

    async def is_logged_in(self, page) -> bool:
        """Проверка авторизации через шаблон или стандартную логику"""
        if (self.template_module and
                hasattr(self.template_module, 'is_logged_in')):
            try:
                return await self.template_module.is_logged_in(page, self.config, self)
            except Exception as e:
                logger.warning(f"Ошибка в шаблонной проверке авторизации: {e}")

        # Стандартная логика как fallback
        return await super().is_logged_in(page)

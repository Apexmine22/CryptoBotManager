# core/bot_manager.py
"""
Менеджер ботов v4.0 - оптимизированная версия
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base_bot import BaseBot, BotStatus
from .config_manager import ConfigManager, UniversalBotConfig
from .template_bot import TemplateBot
from utils.logger import logger


class BotManager:
    """Управление всеми ботами с поддержкой шаблонов"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.bots: Dict[str, BaseBot] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.initialized = False
        self._stop_event = asyncio.Event()
        self.health_check_interval = 60

    async def initialize(self):
        """Инициализация менеджера ботов"""
        if self.initialized:
            return True

        try:
            # Создание необходимых директорий
            Path("data/logs").mkdir(parents=True, exist_ok=True)
            Path("data/cookies").mkdir(parents=True, exist_ok=True)
            Path("data/screenshots").mkdir(parents=True, exist_ok=True)
            Path("templates").mkdir(exist_ok=True)

            # Загрузка конфигурации ботов
            await self.reload_bots()

            self.initialized = True
            logger.success("✅ BotManager инициализирован")

            # Запуск фоновых задач
            asyncio.create_task(self._health_check_loop())

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации BotManager: {e}")
            return False

    async def _create_bot_instance(self, config: UniversalBotConfig) -> bool:
        """Создание экземпляра бота на основе типа"""
        try:
            if hasattr(config, 'template') and config.template:
                bot_instance = TemplateBot(config, self.config_manager)
                logger.info(f"✅ Создан шаблонный бот: {config.name} (шаблон: {config.template})")
            else:
                from .universal_bot import UniversalBot
                bot_instance = UniversalBot(config, self.config_manager)
                logger.info(f"✅ Создан универсальный бот: {config.name}")

            self.bots[config.name] = bot_instance
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка создания бота {config.name}: {e}")
            return False

    async def start_all(self):
        """Запуск всех включенных ботов"""
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return

        enabled_bots = [
            name for name, bot in self.bots.items()
            if bot.config.enabled and name not in self.tasks
        ]

        logger.info(f"🚀 Запуск {len(enabled_bots)} ботов...")

        for bot_name in enabled_bots:
            await self.start_bot(bot_name)

    async def stop_all(self):
        """Остановка всех ботов"""
        if not self.tasks:
            logger.info("ℹ️ Нет запущенных ботов")
            return

        logger.info(f"🛑 Остановка {len(self.tasks)} ботов...")

        for bot_name in list(self.tasks.keys()):
            await self.stop_bot(bot_name)

    async def start_bot(self, bot_name: str) -> bool:
        """Запуск конкретного бота"""
        try:
            if bot_name not in self.bots:
                logger.error(f"❌ Бот не найден: {bot_name}")
                return False

            bot = self.bots[bot_name]

            if not bot.config.enabled:
                logger.warning(f"⚠️ Бот {bot_name} отключен в конфигурации")
                return False

            if bot_name in self.tasks and not self.tasks[bot_name].done():
                logger.info(f"ℹ️ Бот {bot_name} уже запущен")
                return True

            task = asyncio.create_task(self._run_bot_safe(bot_name, bot))
            self.tasks[bot_name] = task

            logger.success(f"🚀 Бот {bot_name} запущен")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота {bot_name}: {e}")
            return False

    async def _run_bot_safe(self, bot_name: str, bot: BaseBot):
        """Безопасный запуск бота"""
        try:
            await bot.run()
        except asyncio.CancelledError:
            logger.info(f"🛑 Бот {bot_name} остановлен")
        except Exception as e:
            logger.error(f"❌ Бот {bot_name} завершился с ошибкой: {e}")
        finally:
            self.tasks.pop(bot_name, None)

    async def stop_bot(self, bot_name: str) -> bool:
        """Остановка конкретного бота"""
        try:
            if bot_name not in self.tasks:
                logger.warning(f"⚠️ Бот {bot_name} не запущен")
                return True

            bot = self.bots[bot_name]
            await bot.stop()

            task = self.tasks[bot_name]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.tasks.pop(bot_name, None)
            logger.info(f"🛑 Бот {bot_name} остановлен")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка остановки бота {bot_name}: {e}")
            return False

    async def restart_bot(self, bot_name: str) -> bool:
        """Перезапуск бота"""
        try:
            await self.stop_bot(bot_name)
            await asyncio.sleep(2)
            return await self.start_bot(bot_name)
        except Exception as e:
            logger.error(f"❌ Ошибка перезапуска бота {bot_name}: {e}")
            return False

    def get_bot_status(self, bot_name: str) -> Optional[Dict[str, Any]]:
        """Получение статуса бота"""
        if bot_name not in self.bots:
            return None

        bot = self.bots[bot_name]
        is_running = bot_name in self.tasks and not self.tasks[bot_name].done()

        bot_type = "TemplateBot" if hasattr(bot, 'template_name') else "UniversalBot"
        template_name = getattr(bot, 'template_name', 'N/A') if hasattr(bot, 'template_name') else 'N/A'

        return {
            "name": bot_name,
            "type": bot_type,
            "template": template_name,
            "status": bot.status,
            "stats": bot.stats,
            "is_running": is_running,
            "enabled": bot.config.enabled,
            "config": bot.config
        }

    def get_all_bot_statuses(self) -> List[Dict[str, Any]]:
        """Получение статусов всех ботов"""
        return [self.get_bot_status(name) for name in self.bots if self.get_bot_status(name) is not None]

    def get_bot_count(self) -> int:
        """Получение количества ботов"""
        return len(self.bots)

    def get_running_bot_count(self) -> int:
        """Получение количества запущенных ботов"""
        return len([t for t in self.tasks.values() if not t.done()])

    async def _health_check_loop(self):
        """Фоновая проверка здоровья ботов"""
        while not self._stop_event.is_set():
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"❌ Ошибка в health check: {e}")
                await asyncio.sleep(30)

    async def _perform_health_check(self):
        """Выполнение проверки здоровья"""
        for bot_name, task in list(self.tasks.items()):
            if task.done():
                logger.warning(f"⚠️ Бот {bot_name} завершил работу, перезапуск...")
                self.tasks.pop(bot_name, None)
                if bot_name in self.bots and self.bots[bot_name].config.enabled:
                    await self.restart_bot(bot_name)

    async def shutdown(self):
        """Завершение работы менеджера"""
        self._stop_event.set()
        await self.stop_all()
        self.initialized = False
        logger.info("✅ BotManager завершил работу")

    async def reload_bots(self):
        """Перезагрузка ботов из конфигурации"""
        await self.stop_all()
        self.bots.clear()

        # Загрузка конфигурации ботов
        bot_configs = self.config_manager.get_universal_bot_configs()
        creation_tasks = [self._create_bot_instance(config) for config in bot_configs]
        results = await asyncio.gather(*creation_tasks, return_exceptions=True)

        successful_creations = sum(1 for result in results if result is True)
        logger.info(f"✅ Перезагружено {successful_creations}/{len(bot_configs)} ботов")
# core/base_bot.py
"""
Базовый класс бота v2.0 - оптимизированная архитектура
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

from utils.logger import logger


class BotStatus(Enum):
    """Статусы бота"""
    STOPPED = "⏹️ Остановлен"
    RUNNING = "🟢 Запущен"
    WORKING = "⚡ Работает"
    ERROR = "❌ Ошибка"
    WAITING = "⏳ Ожидание"
    LOGGING_IN = "🔐 Авторизация"
    SOLVING_CAPTCHA = "🧩 Капча"
    COLLECTING_REWARD = "💰 Награда"
    NAVIGATING = "🧭 Навигация"
    RESTARTING = "🔄 Перезапуск"


@dataclass
class BotStats:
    """Статистика бота"""
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0
    cycles_completed: int = 0
    captchas_solved: int = 0
    current_action: str = "Ожидание запуска"
    last_error: str = ""
    last_success: float = 0.0
    avg_cycle_time: float = 0.0
    consecutive_errors: int = 0


class BaseBot(ABC):
    """Базовый класс для всех ботов"""

    def __init__(self, config, config_manager):
        self.config = config
        self.config_manager = config_manager
        self.status = BotStatus.STOPPED
        self.stats = BotStats()
        self._stop_event = asyncio.Event()
        self._browser_manager = None
        self._captcha_solver = None
        self._cycle_start_time = 0
        self._max_consecutive_errors = getattr(config, 'max_consecutive_errors', 5)

        # Создание директорий
        self.data_dir = Path("data")
        self.cookies_dir = self.data_dir / "cookies"
        self.screenshots_dir = self.data_dir / "screenshots"
        self.logs_dir = self.data_dir / "logs"

        for directory in [self.data_dir, self.cookies_dir,
                          self.screenshots_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Инициализация бота"""
        self.update_status(BotStatus.RUNNING, "Инициализация компонентов")

        try:
            from .browser_manager import BrowserManager
            from .captcha_solver import CaptchaSolver

            self._browser_manager = BrowserManager(self.config_manager)
            self._captcha_solver = CaptchaSolver(self.config_manager)

            success = await self._browser_manager.initialize()
            if not success:
                self.update_status(BotStatus.ERROR, "Ошибка инициализации браузера")
                return False

            self.update_status(BotStatus.RUNNING, "Готов к работе")
            return True

        except Exception as e:
            self.update_status(BotStatus.ERROR,
                               f"Ошибка инициализации: {e}")
            logger.error(f"Ошибка инициализации бота {self.config.name}: {e}")
            return False

    async def run(self):
        """Основной цикл выполнения"""
        if not await self.initialize():
            return

        cycle_count = 0
        self.stats.last_success = time.time()

        try:
            while not self._stop_event.is_set() and self.config.enabled:
                cycle_count += 1
                self._cycle_start_time = time.time()

                try:
                    success = await self.execute_cycle()
                    cycle_time = time.time() - self._cycle_start_time

                    if success:
                        self._on_cycle_success(cycle_time, cycle_count)
                    else:
                        self._on_cycle_failure(cycle_count)

                    if self.stats.consecutive_errors >= self._max_consecutive_errors:
                        self.update_status(
                            BotStatus.ERROR,
                            "Слишком много ошибок подряд",
                        )
                        if getattr(self.config, 'stop_on_critical_error', True):
                            break

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._on_cycle_exception(e, cycle_count)

                # Умная задержка перед следующим запуском
                if not self._stop_event.is_set() and self.config.enabled:
                    await self._smart_delay()

        except Exception as e:
            self.update_status(BotStatus.ERROR,
                               f"Критическая ошибка: {e}")
            logger.error(f"Критическая ошибка в боте {self.config.name}: {e}")
        finally:
            await self.cleanup()
            self.update_status(BotStatus.STOPPED, "Работа завершена")

    async def execute_cycle(self) -> bool:
        """Выполнение одного цикла работы"""
        try:
            self.update_status(BotStatus.WORKING, "Подготовка браузера")

            browser, page = await self._browser_manager.create_browser()
            if not page:
                return False

            await self._load_cookies_with_timeout(page)

            if not await self.is_logged_in(page):
                self.update_status(BotStatus.LOGGING_IN,
                                   "Выполнение авторизации")
                if not await self.login(page):
                    await browser.close()
                    return False

            self.update_status(BotStatus.WORKING,
                               "Выполнение действий")
            result = await self.perform_actions(page)

            if result:
                await self.save_cookies(page)
                self.stats.last_success = time.time()

            await browser.close()
            return result

        except Exception as e:
            self.update_status(BotStatus.ERROR,
                               f"Ошибка цикла: {e}")
            logger.error(f"Ошибка выполнения цикла в боте {self.config.name}: {e}")
            return False

    def _on_cycle_success(self, cycle_time: float, cycle_count: int):
        """Обработка успешного цикла"""
        self.stats.success_count += 1
        self.stats.consecutive_errors = 0
        self.stats.cycles_completed += 1
        self.stats.total_time += cycle_time
        if self.stats.cycles_completed > 0:
            self.stats.avg_cycle_time = self.stats.total_time / self.stats.cycles_completed
        self.stats.current_action = (f"Цикл {cycle_count} завершен "
                                    f"успешно за {cycle_time:.1f} с")

    def _on_cycle_failure(self, cycle_count: int):
        """Обработка неудачного цикла"""
        self.stats.failure_count += 1
        self.stats.consecutive_errors += 1
        self.stats.cycles_completed += 1
        self.stats.current_action = f"Ошибка в цикле {cycle_count}"

    def _on_cycle_exception(self, error: Exception, cycle_count: int):
        """Обработка исключения в цикле"""
        self.stats.failure_count += 1
        self.stats.consecutive_errors += 1
        self.stats.last_error = str(error)
        self.stats.current_action = (f"Исключение в цикле {cycle_count}: "
                                    f"{error}")

    async def _smart_delay(self):
        """Умная задержка между циклами"""
        base_delay = getattr(self.config, 'cycle_delay', 300)

        if self.stats.consecutive_errors > 0:
            base_delay *= (1 + self.stats.consecutive_errors * 0.5)

        delay = max(30, min(base_delay, 3600))

        self.update_status(BotStatus.WAITING,
                           f"Ожидание {int(delay)} с")
        await asyncio.sleep(delay)

    async def _load_cookies_with_timeout(self, page, timeout: int = 5):
        """Загрузка куков с таймаутом"""
        try:
            await asyncio.wait_for(self.load_cookies(page), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут загрузки куков для {self.config.name}")

    def update_status(self, status: BotStatus, message: str = ""):
        """Обновление статуса бота"""
        self.status = status
        self.stats.current_action = message
        logger.info(f"[{self.config.name}] {status.value}: {message}")

    async def load_cookies(self, page):
        """Загрузка куков из файла"""
        try:
            cookie_file = self.cookies_dir / f"{self.config.name}_cookies.json"
            if cookie_file.exists():
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)

                if cookies:
                    await page.context.add_cookies(cookies)
                    return True
        except Exception as e:
            logger.warning(f"Ошибка загрузки куков {self.config.name}: {e}")
        return False

    async def save_cookies(self, page):
        """Сохранение куков в файл"""
        try:
            cookies = await page.context.cookies()
            if cookies:
                cookie_file = self.cookies_dir / f"{self.config.name}_cookies.json"
                with open(cookie_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                return True
        except Exception as e:
            logger.warning(f"Ошибка сохранения куков {self.config.name}: {e}")
        return False

    async def is_logged_in(self, page) -> bool:
        """Проверка статуса авторизации"""
        try:
            cur = page.url.lower()
            if any(key in cur for key in ['login', 'signin', 'auth']):
                return False

            logout_indicators = [
                "logout", "sign out", "выход", "выйти",
                "log out", "signout", "exit", "quit"
            ]

            page_content = (await page.content()).lower()
            has_logout = any(ind in page_content for ind in logout_indicators)

            has_user_elements = any(
                await page.is_visible(selector) for selector in
                ['.user', '.account', '.profile', '[class*="user"]']
            )
            return has_logout or has_user_elements

        except Exception:
            return False

    async def stop(self):
        """Остановка бота"""
        self.update_status(BotStatus.STOPPED, "Запрос на остановку")
        self._stop_event.set()
        await self.cleanup()

    async def cleanup(self):
        """Очистка ресурсов"""
        if self._browser_manager:
            await self._browser_manager.cleanup()
        self._stop_event.clear()

    async def restart(self):
        """Перезапуск бота"""
        self.update_status(BotStatus.RESTARTING, "Перезапуск")
        await self.stop()
        await asyncio.sleep(2)
        await self.run()

    @abstractmethod
    async def login(self, page) -> bool:
        """Логика авторизации"""
        pass

    @abstractmethod
    async def perform_actions(self, page) -> bool:
        """Основные действия бота"""
        pass

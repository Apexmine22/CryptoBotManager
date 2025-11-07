# core/universal_bot.py
"""
Универсальный бот v3.1 - исправленная версия
"""

import asyncio
import datetime
import random
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from .base_bot import BaseBot, BotStatus
from .config_manager import UniversalBotConfig
from .captcha_solver import CaptchaSolver
from utils.logger import logger


@dataclass
class ActionResult:
    """Результат выполнения действия"""
    success: bool
    message: str = ""
    data: Any = None
    needs_retry: bool = False


class UniversalBot(BaseBot):
    """Современный универсальный бот с улучшенной логикой и обработкой ошибок"""

    def __init__(self, config: UniversalBotConfig, config_manager):
        super().__init__(config, config_manager)
        self.universal_config = config
        self.session_stats = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'captchas_solved': 0,
            'pages_visited': 0,
        }
        self._current_page: Optional[Page] = None
        self._captcha_solver = None

    async def initialize(self):
        """Расширенная инициализация бота"""
        await super().initialize()
        if self._captcha_solver is None:
            self._captcha_solver = CaptchaSolver(self.config_manager)
        return True

    # ------------------------------------------------------------------
    #   ОСНОВНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------

    async def login(self, page: Page) -> bool:
        """Улучшенная система авторизации с расширенными стратегиями и мониторингом"""
        try:
            self.update_status(BotStatus.LOGGING_IN, "🔄 Начало процесса авторизации")
            self.session_stats['total_attempts'] += 1
            self._current_page = page

            # Подготовка страницы
            await self._prepare_page(page)

            # Проверка, не авторизованы ли мы уже
            if await self._verify_login_success(page):
                self.update_status(BotStatus.RUNNING, "✅ Уже авторизован")
                self.session_stats['successful_attempts'] += 1
                return True

            # Расширенный список стратегий авторизации с приоритетами
            login_strategies = [
                {"name": "Прямая авторизация", "method": self._try_direct_login, "priority": 1},
                {"name": "Навигация по URL", "method": self._try_navigation_login, "priority": 2},
                {"name": "Автоопределение формы", "method": self._try_form_detection_login, "priority": 3},
                {"name": "Поиск ссылки логина", "method": self._try_login_link_navigation, "priority": 4},
                {"name": "Аварийная навигация", "method": self._try_emergency_navigation, "priority": 5},
            ]

            # Сортировка по приоритету
            login_strategies.sort(key=lambda x: x["priority"])

            max_attempts = self.universal_config.settings.max_retries
            attempts = 0

            for strategy in login_strategies:
                if attempts >= max_attempts:
                    break

                strategy_name = strategy["name"]
                strategy_method = strategy["method"]

                self.update_status(BotStatus.LOGGING_IN, f"🔄 Попытка: {strategy_name}")
                logger.info(f"[{self.config.name}] Попытка авторизации: {strategy_name}")

                try:
                    # Выполнение стратегии
                    success = await strategy_method(page)

                    if success:
                        # Дополнительная проверка успешности авторизации
                        await self._random_delay(2, 3)
                        if await self._verify_login_success(page):
                            self.update_status(BotStatus.RUNNING, f"✅ Успешная авторизация через {strategy_name}")
                            self.session_stats['successful_attempts'] += 1

                            # Сохранение куков после успешной авторизации
                            await self.save_cookies(page)

                            logger.success(f"[{self.config.name}] Авторизация успешна через {strategy_name}")
                            return True
                        else:
                            logger.warning(
                                f"[{self.config.name}] Стратегия {strategy_name} завершилась, но авторизация не подтверждена")
                            success = False

                    if not success:
                        attempts += 1
                        logger.debug(
                            f"[{self.config.name}] Стратегия {strategy_name} не удалась, попытка {attempts}/{max_attempts}")

                        # Задержка между попытками с прогрессивным увеличением
                        delay = min(5 + attempts * 2, 15)  # От 5 до 15 секунд
                        await self._random_delay(delay - 1, delay + 1)

                        # Перезагрузка страницы после неудачной попытки (кроме последней)
                        if attempts < max_attempts:
                            await self._safe_reload(page)

                except Exception as e:
                    attempts += 1
                    logger.error(f"[{self.config.name}] Ошибка в стратегии {strategy_name}: {e}")
                    await self._random_delay(3, 5)

            # Все стратегии провалились - финальная проверка
            self.update_status(BotStatus.LOGGING_IN, "🔍 Финальная проверка авторизации")
            if await self._verify_login_success(page):
                self.update_status(BotStatus.RUNNING, "✅ Авторизация успешна (проверка после всех попыток)")
                self.session_stats['successful_attempts'] += 1
                await self.save_cookies(page)
                return True

            self.update_status(BotStatus.ERROR, "❌ Все стратегии авторизации провалились")
            self.session_stats['failed_attempts'] += 1

            # Сохранение скриншота при ошибке
            if self.universal_config.settings.screenshot_on_error:
                await self._take_error_screenshot(page, "login_failed")

            logger.error(f"[{self.config.name}] Все {attempts} попыток авторизации провалились")
            return False

        except Exception as e:
            error_msg = f"Критическая ошибка авторизации: {e}"
            self.update_status(BotStatus.ERROR, error_msg)
            self.session_stats['failed_attempts'] += 1
            logger.error(f"[{self.config.name}] {error_msg}")
            return False

    async def _try_login_link_navigation(self, page: Page) -> bool:
        """Стратегия поиска и перехода по ссылке логина"""
        try:
            login_link_selectors = [
                self.universal_config.login_selectors.login_link,
                'a[href*="login"]',
                'a[href*="signin"]',
                'a[href*="auth"]',
                'a:has-text("Login")',
                'a:has-text("Sign In")',
                'a:has-text("Войти")',
                'a:has-text("Вход")',
            ]

            for selector in login_link_selectors:
                if not selector:
                    continue

                try:
                    if await page.is_visible(selector):
                        await page.click(selector)
                        await self._wait_for_navigation(page)
                        await self._random_delay(2, 4)

                        # Попытка стандартной авторизации после перехода
                        return await self._try_direct_login(page)
                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Стратегия ссылки логина не удалась: {e}")
            return False

    async def _try_emergency_navigation(self, page: Page) -> bool:
        """Аварийная стратегия навигации"""
        try:
            # Попытка перехода на основные URL
            base_urls = [
                self.universal_config.url + "/login",
                self.universal_config.url + "/signin",
                self.universal_config.url + "/auth",
                self.universal_config.url + "/account",
                self.universal_config.url + "/user",
            ]

            for url in base_urls:
                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._random_delay(3, 5)

                    # Проверка авторизации
                    if await self._verify_login_success(page):
                        return True

                    # Попытка прямой авторизации
                    if await self._try_direct_login(page):
                        return True

                except Exception:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Аварийная навигация не удалась: {e}")
            return False

    async def _safe_reload(self, page: Page):
        """Безопасная перезагрузка страницы"""
        try:
            await page.reload(wait_until="domcontentloaded")
            await self._random_delay(2, 4)
        except Exception as e:
            logger.debug(f"Ошибка перезагрузки страницы: {e}")

    async def _take_error_screenshot(self, page: Page, error_type: str):
        """Создание скриншота при ошибке"""
        try:
            screenshot_dir = Path("data/screenshots")
            screenshot_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.config.name}_{error_type}_{timestamp}.png"
            screenshot_path = screenshot_dir / filename

            await page.screenshot(path=screenshot_path)
            logger.info(f"Скриншот ошибки сохранен: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Не удалось сохранить скриншот ошибки: {e}")
    async def perform_actions(self, page: Page) -> bool:
        """Выполнение основных действий с улучшенной логикой"""
        try:
            self.update_status(BotStatus.WORKING, "Начало выполнения действий")
            self.session_stats['total_attempts'] += 1
            self._current_page = page

            # Навигация к целевой странице
            if not await self._navigate_to_actions_page(page):
                self.update_status(BotStatus.ERROR, "Не удалось перейти к действиям")
                return False

            # Определение доступных действий
            available_actions = await self._detect_available_actions(page)
            if not available_actions:
                self.update_status(BotStatus.WAITING, "Действия недоступны")
                return True

            # Выполнение действий в приоритетном порядке
            executed = False
            for action_name in available_actions:
                action_result = await self._execute_action(page, action_name)
                if action_result.success:
                    executed = True
                    if action_result.message:
                        self.update_status(BotStatus.COLLECTING_REWARD, action_result.message)
                    break

            if executed:
                self.session_stats['successful_attempts'] += 1
                self.update_status(BotStatus.WAITING, "Действия выполнены успешно")
            else:
                self.session_stats['failed_attempts'] += 1
                self.update_status(BotStatus.WAITING, "Действия завершены")

            return executed

        except Exception as e:
            self.update_status(BotStatus.ERROR, f"Ошибка выполнения действий: {e}")
            self.session_stats['failed_attempts'] += 1
            return False

    # ------------------------------------------------------------------
    #   СТРАТЕГИИ АВТОРИЗАЦИИ
    # ------------------------------------------------------------------

    async def _try_direct_login(self, page: Page) -> bool:
        """Прямая авторизация через известные селекторы"""
        selectors = self.universal_config.login_selectors

        try:
            # Проверка доступности полей ввода
            email_field = await self._find_best_selector_match(page, [
                selectors.email_field,
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email" i]',
                'input[placeholder*="mail" i]'
            ])

            password_field = await self._find_best_selector_match(page, [
                selectors.password_field,
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password" i]',
                'input[placeholder*="пароль" i]'
            ])

            if not email_field or not password_field:
                return False

            # Заполнение полей
            await page.fill(email_field, self.universal_config.email)
            await self._random_delay(1, 2)

            await page.fill(password_field, self.universal_config.password)
            await self._random_delay(1, 2)

            # Поиск и нажатие кнопки входа
            login_button = await self._find_best_selector_match(page, [
                selectors.login_button,
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Sign In")',
                'button:has-text("Login")',
                'button:has-text("Войти")',
                'button:has-text("Вход")'
            ])

            if login_button:
                await page.click(login_button)
                await self._wait_for_navigation(page)

            # Проверка успешности авторизации
            await self._random_delay(3, 5)
            return await self._verify_login_success(page)

        except Exception as e:
            logger.debug(f"Прямая авторизация не удалась: {e}")
            return False

    async def _try_navigation_login(self, page: Page) -> bool:
        """Авторизация через навигацию по URL"""
        nav = self.universal_config.navigation
        if not nav.login_url:
            return False

        try:
            login_url = f"{self.universal_config.url}{nav.login_url}"
            await page.goto(login_url, wait_until="domcontentloaded")
            await self._random_delay(2, 4)

            # Попытка стандартной авторизации после перехода
            return await self._try_direct_login(page)

        except Exception as e:
            logger.debug(f"Навигационная авторизация не удалась: {e}")
            return False

    async def _try_form_detection_login(self, page: Page) -> bool:
        """Автоматическое обнаружение и заполнение форм"""
        try:
            # Поиск всех форм на странице
            forms = await page.query_selector_all('form')
            for form in forms:
                # Поиск полей в форме
                email_fields = await form.query_selector_all(
                    'input[type="email"], input[name*="email" i], input[placeholder*="email" i]'
                )
                password_fields = await form.query_selector_all(
                    'input[type="password"], input[name*="password" i]'
                )

                if email_fields and password_fields:
                    # Заполнение первого найденного email поля
                    await email_fields[0].fill(self.universal_config.email)
                    await self._random_delay(1, 2)

                    # Заполнение первого найденного password поля
                    await password_fields[0].fill(self.universal_config.password)
                    await self._random_delay(1, 2)

                    # Поиск кнопки отправки
                    submit_buttons = await form.query_selector_all(
                        'button[type="submit"], input[type="submit"], button:has-text("Sign"), button:has-text("Log")'
                    )
                    if submit_buttons:
                        await submit_buttons[0].click()
                        await self._wait_for_navigation(page)
                        await self._random_delay(3, 5)

                        if await self._verify_login_success(page):
                            return True

            return False

        except Exception as e:
            logger.debug(f"Автоопределение формы не удалось: {e}")
            return False

    # ------------------------------------------------------------------
    #   СИСТЕМА ДЕЙСТВИЙ
    # ------------------------------------------------------------------

    async def _detect_available_actions(self, page: Page) -> List[str]:
        """Обнаружение доступных действий на странице"""
        available_actions = []

        try:
            selectors = self.universal_config.action_selectors

            # Проверка claim действия
            if await self._is_element_available(page, selectors.claim_button):
                available_actions.append('claim')

            # Проверка roll действия
            if await self._is_element_available(page, selectors.roll_button):
                available_actions.append('roll')

            # Проверка faucet действия
            if await self._is_element_available(page, selectors.faucet_button):
                available_actions.append('faucet')

            # Автоматическое обнаружение кнопок по тексту
            button_texts = await page.query_selector_all('button, input[type="button"], a.btn, a.button')
            for button in button_texts:
                text = await button.text_content() or ""
                text_lower = text.lower()

                if any(word in text_lower for word in ['claim', 'collect', 'get', 'получить', 'забрать']):
                    if 'claim' not in available_actions:
                        available_actions.append('claim')
                elif any(word in text_lower for word in ['roll', 'dice', 'кубик', 'кости']):
                    if 'roll' not in available_actions:
                        available_actions.append('roll')
                elif any(word in text_lower for word in ['faucet', 'краны', 'кран']):
                    if 'faucet' not in available_actions:
                        available_actions.append('faucet')

        except Exception as e:
            logger.warning(f"Ошибка обнаружения действий: {e}")

        return available_actions

    async def _execute_action(self, page: Page, action_name: str) -> ActionResult:
        """Выполнение конкретного действия"""
        action_handlers = {
            'claim': self._execute_claim_action,
            'roll': self._execute_roll_action,
            'faucet': self._execute_faucet_action,
        }

        handler = action_handlers.get(action_name)
        if not handler:
            return ActionResult(False, f"Неизвестное действие: {action_name}")

        try:
            # Проверка и решение капчи перед действием
            captcha_result = await self._handle_captcha_before_action(page)
            if not captcha_result:
                return ActionResult(False, "Не удалось решить капчу", needs_retry=True)

            # Выполнение действия
            return await handler(page)

        except Exception as e:
            return ActionResult(False, f"Ошибка выполнения {action_name}: {e}", needs_retry=True)

    async def _execute_claim_action(self, page: Page) -> ActionResult:
        """Выполнение claim действия"""
        selectors = self.universal_config.action_selectors
        claim_selector = await self._find_best_selector_match(page, [
            selectors.claim_button,
            'button:has-text("Claim")',
            'button:has-text("Collect")',
            'button:has-text("Get")',
            'button:has-text("Получить")',
        ])

        if not claim_selector:
            return ActionResult(False, "Кнопка claim не найдена")

        try:
            await self._handle_captcha_before_action(page)
            await page.click(claim_selector)
            await self._wait_for_navigation(page)
            await self._random_delay(3, 5)

            # Проверка результата
            if await self._check_success_indicator(page):
                self.stats.captchas_solved += 1
                self.session_stats['captchas_solved'] += 1
                return ActionResult(True, "Награда успешно получена")

            return ActionResult(False, "Claim выполнен, но результат неясен")

        except Exception as e:
            return ActionResult(False, f"Ошибка claim: {e}")

    async def _execute_roll_action(self, page: Page) -> ActionResult:
        """Выполнение roll действия"""
        selectors = self.universal_config.action_selectors
        roll_selector = await self._find_best_selector_match(page, [
            selectors.roll_button,
            'button:has-text("Roll")',
            'button:has-text("Dice")',
            'button:has-text("Кубик")',
        ])

        if not roll_selector:
            return ActionResult(False, "Кнопка roll не найдена")

        try:
            await page.click(roll_selector)
            await self._random_delay(2, 4)

            # Для roll действий обычно не требуется проверка успеха
            return ActionResult(True, "Roll выполнен")

        except Exception as e:
            return ActionResult(False, f"Ошибка roll: {e}")

    async def _execute_faucet_action(self, page: Page) -> ActionResult:
        """Выполнение faucet действия"""
        selectors = self.universal_config.action_selectors
        faucet_selector = await self._find_best_selector_match(page, [
            selectors.faucet_button,
            'button:has-text("Faucet")',
            'button:has-text("Кран")',
        ])

        if not faucet_selector:
            return ActionResult(False, "Кнопка faucet не найдена")

        try:
            await page.click(faucet_selector)
            await self._wait_for_navigation(page)
            await self._random_delay(4, 6)

            # Проверка результата
            if await self._check_success_indicator(page):
                return ActionResult(True, "Faucet выполнен успешно")

            return ActionResult(False, "Faucet выполнен, но результат неясен")

        except Exception as e:
            return ActionResult(False, f"Ошибка faucet: {e}")

    # ------------------------------------------------------------------
    #   КАПЧА СИСТЕМА
    # ------------------------------------------------------------------

    async def _handle_captcha_before_action(self, page: Page) -> bool:
        """Обработка капчи перед выполнением действия"""
        try:
            # Проверка наличия капчи
            if not await self._check_captcha_present(page):
                return True

            self.update_status(BotStatus.SOLVING_CAPTCHA, f"Решение капчи")

            # Автоматическое определение типа капчи
            # captcha_type = await self._detect_captcha_type(page)
            # if captcha_type == "none":
            #     return True

            content = (await page.content()).lower()

            # Проверка AntiBot
            if ('antibot' in content or
                    await page.query_selector('[rel] img') or
                    await page.query_selector('img[src*="antibot"]')):
                self.stats.captchas_solved += 1
                self.session_stats['captchas_solved'] += 1
                await self._random_delay(2, 3)
                return await self._solve_captcha_by_type(page, "antibot")

            # Проверка hCaptcha
            if (await page.query_selector('[data-sitekey]') or
                    'hcaptcha' in content or
                    await page.query_selector('iframe[src*="hcaptcha.com"]')):
                self.stats.captchas_solved += 1
                self.session_stats['captchas_solved'] += 1
                await self._random_delay(2, 3)
                return await self._solve_captcha_by_type(page, "hcaptcha")

            # Проверка reCAPTCHA
            if (await page.query_selector('.g-recaptcha') or
                    'recaptcha' in content or
                    await page.query_selector('iframe[src*="google.com/recaptcha"]')):
                self.stats.captchas_solved += 1
                self.session_stats['captchas_solved'] += 1
                await self._random_delay(2, 3)
                return await self._solve_captcha_by_type(page, "recaptcha")



            # Решение капчи
            # solved = await self._solve_captcha_by_type(page, captcha_type)
            # if solved:
            #     self.stats.captchas_solved += 1
            #     self.session_stats['captchas_solved'] += 1
            #     await self._random_delay(2, 3)
            #     return True

            return False

        except Exception as e:
            logger.error(f"Ошибка обработки капчи: {e}")
            return False

    async def _detect_captcha_type(self, page: Page) -> str:
        """Улучшенное определение типа капчи"""
        try:
            content = (await page.content()).lower()

            # Проверка hCaptcha
            if (await page.query_selector('[data-sitekey]') or
                    'hcaptcha' in content or
                    await page.query_selector('iframe[src*="hcaptcha.com"]')):
                return "hcaptcha"

            # Проверка reCAPTCHA
            if (await page.query_selector('.g-recaptcha') or
                    'recaptcha' in content or
                    await page.query_selector('iframe[src*="google.com/recaptcha"]')):
                return "recaptcha"

            # Проверка AntiBot
            if ('antibot' in content or
                    await page.query_selector('[rel] img') or
                    await page.query_selector('img[src*="antibot"]')):
                return "antibot"

            # Проверка Image Captcha
            if (await page.query_selector('img[src*="captcha"]') or
                    await page.query_selector('input[name*="captcha"]') or
                    'captcha' in content):
                return "image"

            return "none"

        except Exception as e:
            logger.warning(f"Ошибка определения типа капчи: {e}")
            return "none"

    async def _solve_captcha_by_type(self, page: Page, captcha_type: str) -> bool:
        """Решение капчи по типу"""
        if not self._captcha_solver:
            return False

        try:
            if captcha_type == "hcaptcha":
                site_key = await self._extract_hcaptcha_site_key(page)
                return await self._captcha_solver.solve_hcaptcha(page, site_key, page.url)

            elif captcha_type == "recaptcha":
                site_key = await self._extract_recaptcha_site_key(page)
                return await self._captcha_solver.solve_recaptcha(page, site_key, page.url)

            elif captcha_type == "antibot":
                return await self._captcha_solver.solve_anti_bot(page)

            elif captcha_type == "image":
                return await self._solve_image_captcha(page)

            return False

        except Exception as e:
            logger.error(f"Ошибка решения капчи {captcha_type}: {e}")
            return False

    async def _solve_image_captcha(self, page: Page) -> bool:
        """Решение image captcha"""
        try:
            # Поиск изображения капчи
            img_selectors = [
                'img[src*="captcha"]',
                '.captcha img',
                '#captcha img',
                'img.captcha'
            ]

            for selector in img_selectors:
                img_element = await page.query_selector(selector)
                if img_element:
                    screenshot = await img_element.screenshot()
                    import base64
                    img_b64 = base64.b64encode(screenshot).decode('utf-8')

                    solution = await self._captcha_solver.solve_image_captcha(img_b64)
                    if solution:
                        # Поиск поля для ввода решения
                        input_selectors = [
                            'input[name="captcha"]',
                            'input[name="verification"]',
                            'input[type="text"]',
                            '#captcha',
                            '.captcha-input'
                        ]

                        for input_selector in input_selectors:
                            input_element = await page.query_selector(input_selector)
                            if input_element:
                                await input_element.fill(solution)

                                # Поиск кнопки отправки
                                submit_selectors = [
                                    'button[type="submit"]',
                                    'input[type="submit"]',
                                    'button:has-text("Verify")',
                                    'button:has-text("Submit")'
                                ]

                                for submit_selector in submit_selectors:
                                    submit_element = await page.query_selector(submit_selector)
                                    if submit_element:
                                        await submit_element.click()
                                        await self._random_delay(1, 2)
                                        return True
                        return True
            return False

        except Exception as e:
            logger.error(f"Ошибка решения image captcha: {e}")
            return False

    # ------------------------------------------------------------------
    #   ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ------------------------------------------------------------------

    async def _prepare_page(self, page: Page):
        """Подготовка страницы перед действиями"""
        try:
            # Установка таймаутов
            page.set_default_timeout(self.universal_config.settings.wait_timeout * 1000)
            page.set_default_navigation_timeout(self.universal_config.settings.wait_timeout * 1000 * 2)

            # Блокировка ненужных ресурсов
            if hasattr(self.universal_config.settings,
                       'block_resources') and self.universal_config.settings.block_resources:
                await self._block_unnecessary_resources(page)

        except Exception as e:
            logger.warning(f"Ошибка подготовки страницы: {e}")

    async def _navigate_to_actions_page(self, page: Page) -> bool:
        """Навигация к странице с действиями"""
        nav = self.universal_config.navigation
        navigation_urls = [
            (nav.claim_url, "claim"),
            (nav.faucet_url, "faucet"),
            (nav.dashboard_url, "dashboard"),
            ("/", "home"),
        ]

        for url, page_type in navigation_urls:
            if not url:
                continue

            try:
                full_url = f"{self.universal_config.url}{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                await self._random_delay(2, 4)
                self.session_stats['pages_visited'] += 1

                # Проверка доступности действий
                if await self._detect_available_actions(page):
                    return True

            except Exception as e:
                logger.debug(f"Навигация к {url} не удалась: {e}")
                continue

        return False

    async def _find_best_selector_match(self, page: Page, selectors: List[str]) -> Optional[str]:
        """Поиск лучшего совпадения селектора"""
        for selector in selectors:
            if selector and await page.is_visible(selector):
                return selector
        return None

    async def _is_element_available(self, page: Page, selector: str) -> bool:
        """Проверка доступности элемента"""
        if not selector:
            return False
        return await page.is_visible(selector)

    async def _check_captcha_present(self, page: Page) -> bool:
        """Проверка наличия капчи на странице"""
        try:
            content = (await page.content()).lower()
            captcha_indicators = [
                'captcha', 'hcaptcha', 'recaptcha', 'antibot',
                'data-sitekey', 'g-recaptcha'
            ]

            return any(indicator in content for indicator in captcha_indicators)

        except Exception:
            return False

    async def _check_success_indicator(self, page: Page) -> bool:
        """Проверка индикатора успеха"""
        try:
            selectors = self.universal_config.action_selectors

            # Проверка кастомных индикаторов
            if selectors.success_indicator and await page.is_visible(selectors.success_indicator):
                return True
            if selectors.error_indicator and await page.is_visible(selectors.error_indicator):
                return False

            # Анализ текста страницы
            page_text = (await page.content()).lower()
            success_words = ['success', 'успех', 'получено', 'reward', 'награда', 'claimed', 'successfully']
            error_words = ['error', 'ошибка', 'fail', 'failed', 'try again', 'попробуйте']

            if any(word in page_text for word in success_words):
                return True
            if any(word in page_text for word in error_words):
                return False

            return True  # По умолчанию считаем успехом

        except Exception:
            return True

    async def _verify_login_success(self, page: Page) -> bool:
        """Улучшенная проверка успешности авторизации с множественными стратегиями"""
        try:
            # Стратегия 1: Проверка URL
            current_url = page.url.lower()
            login_indicators = ['login', 'signin', 'auth', 'sign-in', 'log-in', 'авторизац', 'вход']
            if any(keyword in current_url for keyword in login_indicators):
                logger.debug(f"URL содержит индикаторы логина: {current_url}")
                return False

            # Стратегия 2: Проверка элементов выхода/профиля
            logout_indicators = [
                "logout", "sign out", "signout", "log out", "exit", "quit",
                "выход", "выйти", "вийти", "изход", "отвязка"
            ]

            profile_indicators = [
                "profile", "account", "dashboard", "cabinet", "personal",
                "профиль", "аккаунт", "кабинет", "личный", "панель"
            ]

            page_content = (await page.content()).lower()

            # Проверка текстовых индикаторов
            has_logout = any(indicator in page_content for indicator in logout_indicators)
            has_profile = any(indicator in page_content for indicator in profile_indicators)

            # Стратегия 3: Проверка CSS селекторов
            user_selectors = [
                '.user', '.account', '.profile', '.user-menu', '.user-info',
                '.user-name', '.user-avatar', '.user-profile',
                '[class*="user"]', '[class*="account"]', '[class*="profile"]',
                '.dropdown-user', '.nav-user', '.header-user',
                '#user', '#account', '#profile',
                '.user-logged-in', '.logged-in', '.is-logged-in'
            ]

            has_user_elements = False
            for selector in user_selectors:
                try:
                    if await page.is_visible(selector):
                        has_user_elements = True
                        break
                except:
                    continue

            # Стратегия 4: Проверка баланса или финансовых элементов
            balance_indicators = [
                "balance", "wallet", "coins", "tokens", "money", "funds",
                "баланс", "кошелек", "монеты", "токены", "деньги", "счет"
            ]

            has_balance_text = any(indicator in page_content for indicator in balance_indicators)

            # Проверка селектора баланса из конфигурации
            balance_selector = self.universal_config.action_selectors.balance_text
            has_balance_element = balance_selector and await page.is_visible(balance_selector)

            # Стратегия 5: Проверка приветственного сообщения
            welcome_indicators = [
                "welcome", "hello", "hi,", "добро пожаловать", "привет",
                "you are logged in", "вы вошли как", "авторизован"
            ]

            has_welcome = any(indicator in page_content for indicator in welcome_indicators)

            # Стратегия 6: Проверка отсутствия формы логина
            login_form_selectors = [
                'input[type="email"]', 'input[type="password"]',
                'input[name="email"]', 'input[name="password"]',
                '#login-form', '.login-form', 'form[action*="login"]',
                'button[type="submit"]', 'input[type="submit"]'
            ]

            has_login_form = False
            for selector in login_form_selectors:
                try:
                    if await page.is_visible(selector):
                        # Дополнительная проверка - если это форма логина, но пользователь уже авторизован
                        if not await self._is_login_form_visible(page):
                            continue
                        has_login_form = True
                        break
                except:
                    continue

            # Стратегия 7: Проверка по наличию email/username в интерфейсе
            user_identifier_selectors = [
                '[class*="email"]', '[class*="username"]', '[class*="user-name"]',
                '.user-email', '.user-login'
            ]

            has_user_identifier = False
            for selector in user_identifier_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and text.strip() and '@' in text:  # Содержит email
                            has_user_identifier = True
                            break
                except:
                    continue

            # Комплексная оценка авторизации
            positive_indicators = [
                has_logout, has_profile, has_user_elements,
                has_balance_text or has_balance_element, has_welcome, has_user_identifier
            ]

            positive_count = sum(positive_indicators)

            # Исправленное логирование с f-strings
            logger.debug(f"Индикаторы авторизации: logout={has_logout}, profile={has_profile}, "
                         f"user_elements={has_user_elements}, balance={has_balance_text or has_balance_element}, "
                         f"welcome={has_welcome}, user_id={has_user_identifier}, total={positive_count}")

            # Если есть форма логина И мало положительных индикаторов - вероятно не авторизован
            if has_login_form and positive_count < 2:
                logger.debug("Обнаружена форма логина и мало положительных индикаторов")
                return False

            # Минимум 2 положительных индикатора для уверенности
            if positive_count >= 2:
                logger.debug("Авторизация подтверждена (2+ индикатора)")
                return True

            # Если только 1 индикатор - дополнительная проверка
            if positive_count == 1:
                # Особые случаи: только баланс или только профиль
                if has_balance_element or has_profile:
                    logger.debug("Авторизация вероятна (баланс/профиль)")
                    return True

            logger.debug("Авторизация не подтверждена (недостаточно индикаторов)")
            return False

        except Exception as e:
            logger.warning(f"Ошибка проверки авторизации: {e}")
            # В случае ошибки используем консервативный подход
            return False

    async def _is_login_form_visible(self, page: Page) -> bool:
        """Проверка, является ли видимая форма именно формой логина"""
        try:
            # Проверяем, есть ли заполненные поля (значит это не форма логина)
            email_fields = await page.query_selector_all('input[type="email"], input[name="email"]')
            for field in email_fields:
                value = await field.get_attribute('value')
                if value and value.strip():
                    return False  # Поле уже заполнено - не форма логина

            password_fields = await page.query_selector_all('input[type="password"]')
            for field in password_fields:
                value = await field.get_attribute('value')
                if value and value.strip():
                    return False  # Пароль уже заполнен - не форма логина

            # Проверяем текст вокруг формы
            form_text = await page.text_content('form') or ""
            form_text_lower = form_text.lower()
            login_keywords = ['sign in', 'log in', 'login', 'вход', 'авторизац']

            return any(keyword in form_text_lower for keyword in login_keywords)

        except Exception:
            return True  # В случае ошибки считаем что это форма логина

    async def _is_login_form_visible(self, page: Page) -> bool:
        """Проверка, является ли видимая форма именно формой логина"""
        try:
            # Проверяем, есть ли заполненные поля (значит это не форма логина)
            email_fields = await page.query_selector_all('input[type="email"], input[name="email"]')
            for field in email_fields:
                value = await field.get_attribute('value')
                if value and value.strip():
                    return False  # Поле уже заполнено - не форма логина

            password_fields = await page.query_selector_all('input[type="password"]')
            for field in password_fields:
                value = await field.get_attribute('value')
                if value and value.strip():
                    return False  # Пароль уже заполнен - не форма логина

            # Проверяем текст вокруг формы
            form_text = await page.text_content('form') or ""
            form_text_lower = form_text.lower()
            login_keywords = ['sign in', 'log in', 'login', 'вход', 'авторизац']

            return any(keyword in form_text_lower for keyword in login_keywords)

        except Exception:
            return True  # В случае ошибки считаем что это форма логина

    async def _wait_for_navigation(self, page: Page, timeout: int = 10):
        """Ожидание навигации"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout * 1000)
        except PlaywrightTimeoutError:
            pass  # Игнорируем таймаут навигации

    async def _block_unnecessary_resources(self, page: Page):
        """Блокировка ненужных ресурсов"""

        async def route_handler(route):
            resource_type = route.request.resource_type
            if resource_type in ['image', 'font', 'media']:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

    async def _extract_hcaptcha_site_key(self, page: Page) -> Optional[str]:
        """Извлечение site key для hCaptcha"""
        try:
            element = await page.query_selector('[data-sitekey]')
            if element:
                return await element.get_attribute('data-sitekey')
            return None
        except Exception:
            return None

    async def _extract_recaptcha_site_key(self, page: Page) -> Optional[str]:
        """Извлечение site key для reCAPTCHA"""
        try:
            element = await page.query_selector('.g-recaptcha')
            if element:
                return await element.get_attribute('data-sitekey')
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    #   УТИЛИТЫ
    # ------------------------------------------------------------------

    async def _random_delay(self, min_seconds: float, max_seconds: float):
        """Случайная задержка"""
        cfg = self.universal_config.settings
        if cfg.random_delays:
            delay = random.uniform(
                cfg.min_delay or min_seconds,
                cfg.max_delay or max_seconds
            )
        else:
            delay = (min_seconds + max_seconds) / 2
        await asyncio.sleep(delay)

    async def _smart_delay(self, min_seconds: float = 2, max_seconds: float = 4):
        """Умная задержка с учетом текущего состояния"""
        base_delay = random.uniform(min_seconds, max_seconds)

        # Увеличиваем задержку при ошибках
        if self.stats.consecutive_errors > 0:
            base_delay *= (1 + self.stats.consecutive_errors * 0.5)

        await asyncio.sleep(min(30, base_delay))  # Максимум 30 секунд

    async def is_logged_in(self, page: Page) -> bool:
        """Проверка статуса авторизации"""
        return await self._verify_login_success(page)

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Получение детальной статистики"""
        return {
            **self.session_stats,
            'base_stats': {
                'success_count': self.stats.success_count,
                'failure_count': self.stats.failure_count,
                'cycles_completed': self.stats.cycles_completed,
                'captchas_solved': self.stats.captchas_solved,
                'consecutive_errors': self.stats.consecutive_errors,
            }
        }
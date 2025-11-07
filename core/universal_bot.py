# core/universal_bot.py
"""
Универсальный бот v2.0 – улучшенная логика
"""
import asyncio
import random
from typing import Optional
from playwright.async_api import Page

from .base_bot import BaseBot, BotStatus
from .config_manager import UniversalBotConfig
from .captcha_solver import CaptchaSolver
from utils.logger import logger


class UniversalBot(BaseBot):
    """Универсальный бот для работы с faucet‑сайтами"""

    def __init__(self, config: UniversalBotConfig, config_manager):
        """
        Конструктор теперь сразу получает готовый объект ``UniversalBotConfig``.
        Ранее здесь пытались импортировать ``BotConfig``, которого в проекте уже
        нет, что приводило к ImportError.
        """
        # Передаём тот же объект в базовый класс – он умеет работать с теми
        # полями, которые определены в UniversalBotConfig (name, enabled,
        # url, email, password, cycle_delay, currency_delay и др.).
        super().__init__(config, config_manager)

        # Сохраняем копию полной конфигурации для дальнейшего использования.
        self.universal_config = config

        # Статистика конкретного сеанса (отдельно от BaseBot.stats)
        self.session_stats = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'failed_attempts': 0,
            'captchas_solved': 0,
        }

    # ------------------------------------------------------------------
    #   Авторизация
    # ------------------------------------------------------------------
    async def login(self, page) -> bool:
        """Универсальная логика авторизации"""
        try:
            self.update_status(BotStatus.LOGGING_IN, "Начало авторизации")
            self.session_stats['total_attempts'] += 1

            login_url = self.universal_config.navigation.login_url
            full_url = f"{self.universal_config.url}{login_url}" if login_url else self.universal_config.url

            await page.goto(full_url, wait_until="domcontentloaded")
            await self._random_delay(2, 4)

            login_success = await self._try_login_sequence(page)

            if login_success:
                self.update_status(BotStatus.RUNNING, "Авторизация успешна")
                self.session_stats['successful_attempts'] += 1
                return True

            self.update_status(BotStatus.ERROR, "Ошибка авторизации")
            self.session_stats['failed_attempts'] += 1
            return False

        except Exception as e:
            self.update_status(BotStatus.ERROR, f"Ошибка авторизации: {e}")
            self.session_stats['failed_attempts'] += 1
            return False

    # ------------------------------------------------------------------
    #   Последовательность попыток авторизации
    # ------------------------------------------------------------------
    async def _try_login_sequence(self, page) -> bool:
        """Перебираем имеющиеся способы входа."""
        login_methods = [
            self._try_form_login,
            self._try_button_login,
            self._try_link_login,
        ]

        for method in login_methods:
            try:
                if await method(page):
                    return True
            except Exception:
                # Игнорируем отдельные неудачные попытки
                continue
        return False

    # ------------------------------------------------------------------
    #   Авторизация через форму
    # ------------------------------------------------------------------
    async def _try_form_login(self, page) -> bool:
        selectors = self.universal_config.login_selectors

        if selectors.email_field and await page.is_visible(selectors.email_field):
            await page.fill(selectors.email_field, self.universal_config.email)
            await self._random_delay(1, 2)

        if selectors.password_field and await page.is_visible(selectors.password_field):
            await page.fill(selectors.password_field, self.universal_config.password)
            await self._random_delay(1, 2)

        # Обработка капчи перед нажатием кнопки входа
        if await self._handle_captcha(page):
            await self._random_delay(2, 3)

        if selectors.login_button and await page.is_visible(selectors.login_button):
            await page.locator(selectors.login_button).click()
            await self._random_delay(3, 5)

            # Проверяем, не появилась ли капча после нажатия
            if await self._check_captcha_present(page):
                await self._handle_captcha(page)
                await self._random_delay(2, 3)

        return await self.is_logged_in(page)

    # ------------------------------------------------------------------
    #   Авторизация через кнопку
    # ------------------------------------------------------------------
    async def _try_button_login(self, page) -> bool:
        selectors = self.universal_config.login_selectors
        if selectors.login_button and await page.is_visible(selectors.login_button):
            await page.click(selectors.login_button)
            await self._random_delay(3, 5)

            # Проверяем капчу после нажатия
            if await self._check_captcha_present(page):
                await self._handle_captcha(page)
                await self._random_delay(2, 3)

            return await self.is_logged_in(page)
        return False

    # ------------------------------------------------------------------
    #   Авторизация через ссылку
    # ------------------------------------------------------------------
    async def _try_link_login(self, page) -> bool:
        selectors = self.universal_config.login_selectors
        if selectors.login_link and await page.is_visible(selectors.login_link):
            await page.click(selectors.login_link)
            await self._random_delay(2, 4)
            return await self._try_form_login(page)
        return False

    # ------------------------------------------------------------------
    #   Выполнение действий (claim / roll / faucet)
    # ------------------------------------------------------------------
    async def perform_actions(self, page) -> bool:
        """Логика выполнения операций после входа."""
        try:
            self.update_status(BotStatus.WORKING, "Выполнение действий")
            self.session_stats['total_attempts'] += 1

            if not await self._navigate_to_actions(page):
                return False

            # Порядок действий – как было в оригинальном коде
            actions = [
                self._try_claim_action,
                self._try_roll_action,
                self._try_faucet_action,
            ]

            for action in actions:
                try:
                    if await action(page):
                        self.session_stats['successful_attempts'] += 1
                        return True
                except Exception as e:
                    self.stats.last_error = f"{action.__name__}: {e}"
                    continue

            self.session_stats['failed_attempts'] += 1
            self.update_status(BotStatus.WAITING, "Действия завершены")
            return True

        except Exception as e:
            self.update_status(BotStatus.ERROR, f"Ошибка выполнения: {e}")
            self.session_stats['failed_attempts'] += 1
            return False

    # ------------------------------------------------------------------
    #   Навигация к нужным страницам
    # ------------------------------------------------------------------
    async def _navigate_to_actions(self, page) -> bool:
        nav = self.universal_config.navigation
        navigation_urls = [
            (nav.claim_url, "claim"),
            (nav.faucet_url, "faucet"),
            (nav.dashboard_url, "dashboard"),
        ]

        for url, action_type in navigation_urls:
            if not url:
                continue
            try:
                full_url = f"{self.universal_config.url}{url}"
                await page.goto(full_url, wait_until="domcontentloaded")
                await self._random_delay(2, 4)

                if await self._check_action_availability(page, action_type):
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------
    #   Проверка доступности действий
    # ------------------------------------------------------------------
    async def _check_action_availability(self, page, action_type: str) -> bool:
        selectors = self.universal_config.action_selectors

        if action_type == "claim" and selectors.claim_button:
            return await page.is_visible(selectors.claim_button)
        if action_type == "faucet" and selectors.faucet_button:
            return await page.is_visible(selectors.faucet_button)

        return False

    # ------------------------------------------------------------------
    #   Claim
    # ------------------------------------------------------------------
    async def _try_claim_action(self, page) -> bool:
        claim_button = self.universal_config.action_selectors.claim_button
        if not claim_button or not await page.is_visible(claim_button):
            return False

        # Проверяем капчу перед нажатием
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        await page.click(claim_button)
        await self._random_delay(4, 6)

        # Проверяем капчу после нажатия
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        success = await self._check_success_indicator(page)
        if success:
            self.update_status(BotStatus.COLLECTING_REWARD, "Награда получена")
            self.stats.captchas_solved += 1
            self.session_stats['captchas_solved'] += 1
            return True
        return False

    # ------------------------------------------------------------------
    #   Roll
    # ------------------------------------------------------------------
    async def _try_roll_action(self, page) -> bool:
        roll_button = self.universal_config.action_selectors.roll_button
        if not roll_button or not await page.is_visible(roll_button):
            return False

        # Проверяем капчу перед нажатием
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        await page.click(roll_button)
        await self._random_delay(3, 5)

        # Проверяем капчу после нажатия
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        return True

    # ------------------------------------------------------------------
    #   Faucet (доп. действие)
    # ------------------------------------------------------------------
    async def _try_faucet_action(self, page) -> bool:
        faucet_button = self.universal_config.action_selectors.faucet_button
        if not faucet_button or not await page.is_visible(faucet_button):
            return False

        # Проверяем капчу перед нажатием
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        await page.click(faucet_button)
        await self._random_delay(4, 6)

        # Проверяем капчу после нажатия
        if await self._check_captcha_present(page):
            await self._handle_captcha(page)
            await self._random_delay(2, 3)

        return True

    # ------------------------------------------------------------------
    #   Проверка наличия капчи на странице
    # ------------------------------------------------------------------
    async def _check_captcha_present(self, page) -> bool:
        """Проверяет наличие любой капчи на странице"""
        try:
            content = (await page.content()).lower()

            # Проверяем hcaptcha
            if (await page.query_selector('[data-sitekey]') or
                    'hcaptcha' in content or
                    await page.query_selector('iframe[src*="hcaptcha.com"]')):
                return True

            # Проверяем recaptcha
            if (await page.query_selector('.g-recaptcha') or
                    'recaptcha' in content or
                    await page.query_selector('iframe[src*="google.com/recaptcha"]')):
                return True

            # Проверяем antibot
            if ('antibot' in content or
                    await page.query_selector('[rel] img') or
                    await page.query_selector('img[src*="antibot"]')):
                return True

            # Проверяем image captcha
            if (await page.query_selector('img[src*="captcha"]') or
                    'captcha' in content):
                return True

            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    #   Обработка капчи (hcaptcha / recaptcha / antibot / image)
    # ------------------------------------------------------------------
    async def _handle_captcha(self, page) -> bool:
        try:
            captcha_cfg = self.universal_config.captcha
            captcha_type = captcha_cfg.captcha_type

            # Автоматическое определение типа, если указано «auto»
            if captcha_type == "auto":
                captcha_type = await self._detect_captcha_type(page)

            if captcha_type == "none":
                return True

            self.update_status(BotStatus.SOLVING_CAPTCHA,
                               f"Решение {captcha_type}")

            solver = CaptchaSolver(self.config_manager)
            solved = False

            if captcha_type == "hcaptcha":
                site_key = captcha_cfg.site_key or await self._extract_hcaptcha_site_key(page)
                page_url = captcha_cfg.page_url or page.url
                solved = await solver.solve_hcaptcha(page, site_key, page_url)

            elif captcha_type == "recaptcha":
                site_key = captcha_cfg.site_key or await self._extract_recaptcha_site_key(page)
                page_url = captcha_cfg.page_url or page.url
                solved = await solver.solve_recaptcha(page, site_key, page_url)

            elif captcha_type == "antibot":
                solved = await solver.solve_anti_bot(page)

            elif captcha_type == "image":
                img_sel = captcha_cfg.image_selector or 'img[src*="captcha"]'
                solved = await self._solve_image_captcha(page, img_sel)

            if solved:
                self.stats.captchas_solved += 1
                self.session_stats['captchas_solved'] += 1
                await self._random_delay(1, 2)
                return True
            return False

        except Exception as e:
            logger.error(f"Ошибка обработки капчи: {e}")
            return False

    # ------------------------------------------------------------------
    #   Авто‑определение типа капчи (улучшенная версия)
    # ------------------------------------------------------------------
    async def _detect_captcha_type(self, page) -> str:
        try:
            content = (await page.content()).lower()

            # Проверяем hcaptcha
            if (await page.query_selector('[data-sitekey]') or
                    'hcaptcha' in content or
                    await page.query_selector('iframe[src*="hcaptcha.com"]')):
                return "hcaptcha"

            # Проверяем recaptcha
            if (await page.query_selector('.g-recaptcha') or
                    'recaptcha' in content or
                    await page.query_selector('iframe[src*="google.com/recaptcha"]')):
                return "recaptcha"

            # Проверяем antibot
            if ('antibot' in content or
                    await page.query_selector('[rel] img') or
                    await page.query_selector('img[src*="antibot"]')):
                return "antibot"

            # Проверяем image captcha
            if (await page.query_selector('img[src*="captcha"]') or
                    'captcha' in content):
                return "image"

            return "none"
        except Exception:
            return "none"

    # ------------------------------------------------------------------
    #   Извлечение site‑key для hcaptcha
    # ------------------------------------------------------------------
    async def _extract_hcaptcha_site_key(self, page) -> Optional[str]:
        try:
            # Ищем data-sitekey атрибут
            el = await page.query_selector('[data-sitekey]')
            if el:
                return await el.get_attribute('data-sitekey')

            # Ищем в iframe
            iframe = await page.query_selector('iframe[src*="hcaptcha.com"]')
            if iframe:
                src = await iframe.get_attribute('src')
                if 'sitekey=' in src:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(src)
                    params = urllib.parse.parse_qs(parsed.query)
                    return params.get('sitekey', [None])[0]
        except Exception as e:
            logger.error(f"Ошибка извлечения hcaptcha site-key: {e}")
        return None

    # ------------------------------------------------------------------
    #   Извлечение site‑key для recaptcha
    # ------------------------------------------------------------------
    async def _extract_recaptcha_site_key(self, page) -> Optional[str]:
        try:
            # Ищем в div с классом g-recaptcha
            el = await page.query_selector('.g-recaptcha')
            if el:
                return await el.get_attribute('data-sitekey')

            # Ищем в iframe
            iframe = await page.query_selector('iframe[src*="google.com/recaptcha"]')
            if iframe:
                src = await iframe.get_attribute('src')
                if 'k=' in src:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(src)
                    params = urllib.parse.parse_qs(parsed.query)
                    return params.get('k', [None])[0]
        except Exception as e:
            logger.error(f"Ошибка извлечения recaptcha site-key: {e}")
        return None

    # ------------------------------------------------------------------
    #   Решение image‑captcha (base64 → сервис)
    # ------------------------------------------------------------------
    async def _solve_image_captcha(self, page, image_selector: str) -> bool:
        try:
            solver = CaptchaSolver(self.config_manager)
            img_el = await page.query_selector(image_selector)
            if not img_el:
                return False

            screenshot = await img_el.screenshot()
            import base64
            img_b64 = base64.b64encode(screenshot).decode('utf-8')
            solution = await solver.solve_image_captcha(img_b64)

            if not solution:
                return False

            # Попробуем заполнить найденные поля ввода
            input_sel = ['input[name="captcha"]', 'input[type="text"]', '#captcha',
                         'input[name="verification"]', 'input[name="code"]']
            for sel in input_sel:
                if await page.is_visible(sel):
                    await page.fill(sel, solution)
                    break

            # И нажмём кнопку отправки, если она есть
            submit_sel = ['button[type="submit"]', 'input[type="submit"]',
                          'button:has-text("Verify")', 'button:has-text("Submit")']
            for sel in submit_sel:
                if await page.is_visible(sel):
                    await page.click(sel)
                    await self._random_delay(1, 2)
                    return True
            return True
        except Exception as e:
            logger.error(f"Ошибка решения image captcha: {e}")
            return False

    # ------------------------------------------------------------------
    #   Проверка индикатора успеха
    # ------------------------------------------------------------------
    async def _check_success_indicator(self, page) -> bool:
        sel = self.universal_config.action_selectors
        if sel.success_indicator and await page.is_visible(sel.success_indicator):
            return True
        if sel.error_indicator and await page.is_visible(sel.error_indicator):
            return False

        page_text = (await page.content()).lower()
        success_words = ['success', 'успех', 'получено', 'reward', 'награда', 'claimed', 'successfully']
        error_words = ['error', 'ошибка', 'fail', 'failed', 'try again', 'попробуйте']

        if any(word in page_text for word in success_words):
            return True
        if any(word in page_text for word in error_words):
            return False

        return True  # По умолчанию считаем успехом

    # ------------------------------------------------------------------
    #   Случайная задержка (с учётом настроек)
    # ------------------------------------------------------------------
    async def _random_delay(self, min_seconds: float, max_seconds: float):
        cfg = self.universal_config.settings
        if cfg.random_delays:
            min_d = cfg.min_delay or min_seconds
            max_d = cfg.max_delay or max_seconds
            delay = random.uniform(min_d, max_d)
        else:
            delay = (min_seconds + max_seconds) / 2
        await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    #   Проверка, авторизован ли пользователь
    # ------------------------------------------------------------------
    async def is_logged_in(self, page) -> bool:
        try:
            cur = page.url.lower()
            if any(key in cur for key in ['login', 'signin', 'auth']):
                return False

            logout_keys = ["logout", "sign out", "выход", "выйти",
                           "log out", "signout", "exit", "quit"]
            content = (await page.content()).lower()
            if any(word in content for word in logout_keys):
                return True

            selectors = self.universal_config.action_selectors
            has_balance = selectors.balance_text and await page.is_visible(selectors.balance_text)
            has_profile = await page.is_visible('.profile, .account, .user')
            return has_balance or has_profile
        except Exception:
            return False
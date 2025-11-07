# core/browser_manager.py
"""
Менеджер браузера v2.1 - безопасный доступ к конфигурации
"""
import asyncio
import random
import subprocess
import sys
from typing import Optional, Tuple, List
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from utils.logger import logger


@dataclass
class BrowserConfig:
    """Конфигурация браузера по умолчанию"""
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    timeout: int = 30000
    navigation_timeout: int = 60000
    user_agent: str = ""
    disable_javascript: bool = False
    block_resources: bool = True
    proxy_server: str = ""


class BrowserManager:
    """Менеджер браузеров с автоустановкой и безопасной конфигурацией"""

    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.playwright = None
        self.browser_type = None
        self._browser_pool: List[Browser] = []
        self._max_pool_size = 3
        self._initialized = False
        self._default_config = BrowserConfig()

    def _get_safe_config(self) -> BrowserConfig:
        """Безопасное получение конфигурации браузера"""
        try:
            if self.config_manager and hasattr(self.config_manager, 'get_browser_config'):
                return self.config_manager.get_browser_config()
        except Exception as e:
            logger.warning(f"Ошибка получения конфигурации: {e}. Используются значения по умолчанию")

        # Возвращаем конфигурацию по умолчанию
        return self._default_config

    async def install_browsers(self):
        """Автоматическая установка браузеров Playwright"""
        logger.info("Проверка и установка браузеров Playwright...")

        try:
            # Проверяем, установлен ли playwright
            try:
                import playwright
            except ImportError:
                logger.error("Playwright не установлен. Установите: pip install playwright")
                return False

            # Запускаем установку браузеров
            result = subprocess.run([
                sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"
            ], capture_output=True, text=True, timeout=300000)

            if result.returncode == 0:
                logger.info("✅ Браузеры Playwright успешно установлены")
                return True
            else:
                logger.error(f"❌ Ошибка установки браузеров: {result.stderr}")

                # Пробуем установить без зависимостей
                logger.info("Попытка установки без системных зависимостей...")
                result_simple = subprocess.run([
                    sys.executable, "-m", "playwright", "install", "chromium"
                ], capture_output=True, text=True, timeout=300000)

                if result_simple.returncode == 0:
                    logger.info("✅ Браузеры установлены (без системных зависимостей)")
                    return True
                else:
                    logger.error(f"❌ Ошибка простой установки: {result_simple.stderr}")
                    return False

        except subprocess.TimeoutExpired:
            logger.error("❌ Таймаут установки браузеров (более 5 минут)")
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при установке браузеров: {e}")
            return False

    async def check_browsers_installed(self) -> bool:
        """Проверяет, установлены ли браузеры"""
        try:
            result = subprocess.run([
                sys.executable, "-m", "playwright", "list"
            ], capture_output=True, text=True, timeout=30000)

            if result.returncode == 0 and "chromium" in result.stdout.lower():
                logger.info("✅ Браузеры Playwright уже установлены")
                return True
            else:
                logger.warning("❌ Браузеры Playwright не найдены")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить браузеры: {e}")
            return False

    async def initialize(self):
        """Инициализация Playwright с автоустановкой браузеров"""
        if self._initialized:
            return True

        try:
            # Сначала проверяем установлены ли браузеры
            browsers_installed = await self.check_browsers_installed()

            if not browsers_installed:
                logger.info("Запуск автоматической установки браузеров...")
                installation_success = await self.install_browsers()

                if not installation_success:
                    logger.error("Не удалось установить браузеры автоматически")
                    return False

            # Инициализируем Playwright
            self.playwright = await async_playwright().start()

            # Приоритет браузеров
            browser_priority = ['chromium', 'firefox', 'webkit']

            for browser_name in browser_priority:
                try:
                    browser_type = getattr(self.playwright, browser_name)

                    # Пробуем запустить тестовый браузер
                    test_browser = await browser_type.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage'],
                        timeout=30000
                    )

                    # Проверяем что браузер работает
                    page = await test_browser.new_page()
                    await page.goto('about:blank', wait_until='domcontentloaded')
                    await page.close()
                    await test_browser.close()

                    self.browser_type = browser_type
                    self._initialized = True
                    logger.info(f"✅ Инициализирован браузер: {browser_name}")
                    return True

                except Exception as e:
                    logger.warning(f"Браузер {browser_name} недоступен: {e}")

                    # Если браузер не установлен, пробуем установить его
                    if "executable doesn't exist" in str(e):
                        logger.info(f"Попытка установки браузера {browser_name}...")
                        install_result = subprocess.run([
                            sys.executable, "-m", "playwright", "install", browser_name
                        ], capture_output=True, text=True, timeout=180000)

                        if install_result.returncode == 0:
                            logger.info(f"✅ Браузер {browser_name} установлен")
                            # Пробуем снова после установки
                            try:
                                test_browser = await browser_type.launch(
                                    headless=True,
                                    args=['--no-sandbox', '--disable-dev-shm-usage'],
                                    timeout=30000
                                )
                                await test_browser.close()
                                self.browser_type = browser_type
                                self._initialized = True
                                logger.info(f"✅ Инициализирован браузер: {browser_name}")
                                return True
                            except Exception as retry_error:
                                logger.warning(
                                    f"Браузер {browser_name} все еще недоступен после установки: {retry_error}")
                                continue
                        else:
                            logger.warning(f"Не удалось установить браузер {browser_name}")
                    continue

            logger.error("❌ Ни один браузер не доступен для инициализации")
            return False

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Playwright: {e}")
            return False

    async def create_browser(self) -> Tuple[Optional[Browser], Optional[Page]]:
        """Создание браузера и страницы с безопасной конфигурацией"""
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return None, None

        try:
            # Безопасное получение конфигурации
            browser_config = self._get_safe_config()
            browser_args = self._get_browser_args(browser_config)

            browser = await self.browser_type.launch(
                headless=browser_config.headless,
                args=browser_args,
                timeout=30000,
                ignore_default_args=['--enable-automation']
            )

            context = await browser.new_context(
                viewport={
                    "width": browser_config.viewport_width,
                    "height": browser_config.viewport_height
                },
                user_agent=self._get_user_agent(browser_config),
                ignore_https_errors=True,
                java_script_enabled=not browser_config.disable_javascript,
                bypass_csp=True,
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
            )

            await self._apply_anti_detection(context)

            page = await context.new_page()
            page.set_default_timeout(browser_config.timeout)
            page.set_default_navigation_timeout(browser_config.navigation_timeout)

            if browser_config.block_resources:
                await self._block_resources(page)

            # Добавляем в пул для управления
            if len(self._browser_pool) < self._max_pool_size:
                self._browser_pool.append(browser)

            logger.info("✅ Браузер успешно создан")
            return browser, page

        except Exception as e:
            logger.error(f"❌ Ошибка создания браузера: {e}")
            return None, None

    def _get_browser_args(self, browser_config) -> List[str]:
        """Получение аргументов браузера"""
        base_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--no-default-browser-check",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-translate",
            "--mute-audio",
            "--no-first-run",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-backgrounding-occluded-windows",
        ]

        # Безопасная проверка proxy_server
        try:
            if hasattr(browser_config, 'proxy_server') and browser_config.proxy_server:
                base_args.append(f"--proxy-server={browser_config.proxy_server}")
        except AttributeError:
            pass

        return base_args

    def _get_user_agent(self, browser_config) -> str:
        """Получение User-Agent"""
        try:
            if hasattr(browser_config, 'user_agent') and browser_config.user_agent:
                return browser_config.user_agent
        except AttributeError:
            pass

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)

    async def _apply_anti_detection(self, context: BrowserContext):
        """Применение анти‑детекта"""
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en'],
            });

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            window.chrome = {
                app: { isInstalled: false },
                webstore: { onInstallStageChanged: {}, onDownloadProgress: {} },
                runtime: { PlatformOs: { MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd' } }
            };

            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) Iris(TM) Graphics 6100';
                }
                return getParameter(parameter);
            };
        """)

    async def _block_resources(self, page: Page):
        """Блокировка ресурсов"""

        async def route_handler(route):
            resource_type = route.request.resource_type
            if resource_type in ['image', 'font', 'media']:
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", route_handler)

    async def close_browser(self, browser: Browser):
        """Закрытие конкретного браузера"""
        try:
            if browser in self._browser_pool:
                self._browser_pool.remove(browser)
            await browser.close()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии браузера: {e}")

    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка ресурсов BrowserManager...")

        for browser in self._browser_pool[:]:
            try:
                await browser.close()
                self._browser_pool.remove(browser)
            except Exception as e:
                logger.warning(f"Ошибка при закрытии браузера из пула: {e}")

        self._browser_pool.clear()

        if self.playwright:
            try:
                await self.playwright.stop()
                self.playwright = None
            except Exception as e:
                logger.warning(f"Ошибка при остановке Playwright: {e}")

        self._initialized = False
        logger.info("✅ Ресурсы BrowserManager очищены")
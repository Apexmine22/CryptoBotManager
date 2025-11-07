# core/browser_manager.py
"""
Менеджер браузера v2.0 - оптимизированное управление
"""
import asyncio
import random
from typing import Optional, Tuple, List

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from .config_manager import ConfigManager
from utils.logger import logger


class BrowserManager:
    """Менеджер браузеров"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.playwright = None
        self.browser_type = None
        self._browser_pool: List[Browser] = []
        self._max_pool_size = 3
        self._initialized = False

    async def initialize(self):
        """Инициализация Playwright"""
        if self._initialized:
            return True

        try:
            self.playwright = await async_playwright().start()

            browser_priority = ['chromium', 'firefox', 'webkit']

            for browser_name in browser_priority:
                try:
                    browser_type = getattr(self.playwright, browser_name)

                    test_browser = await browser_type.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage'],
                        timeout=15000
                    )
                    await test_browser.close()

                    self.browser_type = browser_type
                    self._initialized = True
                    logger.info(f"Инициализирован браузер: {browser_name}")
                    return True

                except Exception as e:
                    logger.warning(f"Браузер {browser_name} недоступен: {e}")
                    continue

            logger.error("Ни один браузер не доступен для инициализации")
            return False

        except Exception as e:
            logger.error(f"Ошибка инициализации Playwright: {e}")
            return False

    async def create_browser(self) -> Tuple[Optional[Browser], Optional[Page]]:
        """Создание браузера и страницы"""
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return None, None

        try:
            browser_config = self.config_manager.get_browser_config()
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

            return browser, page

        except Exception as e:
            logger.error(f"Ошибка создания браузера: {e}")
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
        # Параметры `--disable-javascript` и `--disable-css` управляются
        # через свойства Playwright, поэтому их убираем из списка.
        return base_args

    def _get_user_agent(self, browser_config) -> str:
        """Получение User-Agent"""
        if browser_config.user_agent:
            return browser_config.user_agent

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

            Object.defineProperty(navigator, 'userAgent', {
                get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            });
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

    async def cleanup(self):
        """Очистка ресурсов"""
        for browser in self._browser_pool:
            try:
                await browser.close()
            except Exception:
                pass

        self._browser_pool.clear()

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        self._initialized = False

# core/captcha_solver.py
"""
Решатель капч v2.0
"""
import aiohttp
import asyncio
import base64
from typing import Optional, Dict, Any, List

from playwright.async_api import Page

from .config_manager import ConfigManager
from utils.logger import logger


class CaptchaSolver:
    """Решение капч через API сервисы"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get_captcha_config()

    async def solve_anti_bot(self, page):
        """Решение AntiBot"""
        try:
            if not page or page.is_closed():
                logger.error("Страница недоступна для решения капчи")
                return

            await asyncio.sleep(5)
            img_main = await self.parse_main_captcha_image(page)
            data = await self.parse_images_from_links(page)

            if not img_main:
                logger.error("Не удалось получить основное изображение капчи")
                return

            captcha_data = {
                "key": self.config.api_key,
                "method": "antibot",
                "main": img_main
            }

            for item in data:
                captcha_data[item['rel']] = item['src']

            AntiBotLinkClick = await self._solve_captcha(captcha_data)

            if not AntiBotLinkClick:
                logger.error("Не получен ответ от сервиса капчи")
                return

            rel_values = str(AntiBotLinkClick).split(",")

            for rel_value in rel_values:
                if rel_value and rel_value.strip():
                    try:
                        await page.locator(f'[rel="{rel_value.strip()}"]').click()
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.warning(f"Не удалось кликнуть по rel={rel_value}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Ошибка в solve_anti_bot: {e}")

    async def solve_hcaptcha(self, page, sitekey: str = None, pageurl: str = None) -> bool:
        """Решение hCaptcha"""
        try:
            if not sitekey:
                sitekey = await page.get_attribute('[data-sitekey]', 'data-sitekey')
            if not pageurl:
                pageurl = page.url

            if not sitekey:
                logger.error("Не найден sitekey для hCaptcha")
                return False

            data = {
                "method": "hcaptcha",
                "sitekey": sitekey,
                "pageurl": pageurl,
                "key": self.config.api_key
            }

            solution = await self._solve_captcha(data)
            if solution:
                await page.evaluate(f"""
                    () => {{
                        const textarea = document.querySelector('[name="h-captcha-response"]');
                        if (textarea) textarea.value = '{solution}';
                    }}
                """)
                logger.success("hCaptcha решена")
                return True

            return False

        except Exception as e:
            logger.error(f"Ошибка решения hCaptcha: {e}")
            return False

    async def solve_image_captcha(self, image_data: str) -> Optional[str]:
        """Решение image captcha"""
        try:
            data = {
                "method": "base64",
                "body": image_data,
                "key": self.config.api_key
            }
            return await self._solve_captcha(data)
        except Exception as e:
            logger.error(f"Ошибка решения image captcha: {e}")
            return None

    async def _solve_captcha(self, data: Dict[str, Any]) -> Optional[str]:
        """Общий метод решения капчи"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.config.service_url}/in.php", data=data) as response:
                    result = await response.text()

            if result.startswith("OK|"):
                captcha_id = result.split("|")[1]
                return await self._get_captcha_result(captcha_id)
            else:
                logger.error(f"Ошибка отправки капчи: {result}")
                return None

        except Exception as e:
            logger.error(f"Ошибка решения капчи: {e}")
            return None

    async def _get_captcha_result(self, captcha_id: str) -> Optional[str]:
        """Получение результата решения капчи"""
        max_attempts = self.config.timeout // self.config.sleep

        for attempt in range(max_attempts):
            await asyncio.sleep(self.config.sleep)

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.config.service_url}/res.php", params={
                        "key": self.config.api_key,
                        "id": captcha_id
                    }) as response:
                        result = await response.text()

                if result.startswith("OK|"):
                    return result.split("|")[1]
                elif "CAPCHA_NOT_READY" in result:
                    continue
                else:
                    logger.error(f"Ошибка получения результата: {result}")
                    break

            except Exception as e:
                logger.warning(f"Ошибка запроса результата: {e}")
                continue

        logger.error("Таймаут решения капчи")
        return None

    async def parse_images_from_links(self, page: Page) -> List[Dict[str, str]]:
        """Парсинг изображений из ссылок"""
        try:
            if not page or page.is_closed():
                logger.error("Страница не доступна для парсинга изображений")
                return []

            images_data = []
            links = await page.query_selector_all('a[rel]')
            logger.info(f"Найдено ссылок с rel: {len(links)}")

            for i, link in enumerate(links):
                try:
                    rel = await link.get_attribute('rel')
                    img = await link.query_selector('img')

                    if img and rel:
                        screenshot = await img.screenshot()
                        if screenshot:
                            image_data = base64.b64encode(screenshot).decode('utf-8')
                            images_data.append({
                                'rel': rel,
                                'src': image_data
                            })
                except Exception as e:
                    logger.warning(f"Ошибка при обработке ссылки {i + 1}: {str(e)}")
                    continue

            logger.info(f"Успешно спарсено изображений: {len(images_data)}")
            return images_data
        except Exception as e:
            logger.error(f"Ошибка парсинга изображений: {str(e)}")
            return []

    async def parse_main_captcha_image(self, page: Page) -> Optional[str]:
        """Парсинг основного изображения капчи"""
        try:
            if not page or page.is_closed():
                logger.error("Страница недоступна для парсинга капчи")
                return None

            main_img = await page.query_selector('img')
            if main_img:
                screenshot = await main_img.screenshot()
                image_data = base64.b64encode(screenshot).decode('utf-8')
                return image_data

            logger.warning("Основное изображение капчи не найдено")
            return None
        except Exception as e:
            logger.error(f"Ошибка парсинга основной капчи: {str(e)}")
            return None

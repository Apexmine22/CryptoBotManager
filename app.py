import wx
import wx.adv
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any

from core.config_manager import ConfigManager
from core.bot_manager import BotManager
from utils.logger import logger
from ui.settings import SettingsDialog
from ui.AddBot import AddBotDialog
from ui.EditBotDialog import EditBotDialog


class BotManagerFrame(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title="Crypto Bot Manager v2.0", size=(1200, 800))

        self.config_manager = None
        self.bot_manager = None
        self.bot_statuses = {}
        self.async_thread = None
        self.running = False
        self.loop = None  # Добавляем ссылку на event loop

        self._init_ui()
        self._create_menu()
        self._setup_async()

        self.Center()
        self.Show()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Панель управления
        control_panel = self._create_control_panel(panel)
        main_sizer.Add(control_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Панель статуса
        status_panel = self._create_status_panel(panel)
        main_sizer.Add(status_panel, 1, wx.EXPAND | wx.ALL, 5)

        # Статус бар
        self.CreateStatusBar()
        self.SetStatusText("Готов к работе")

        panel.SetSizer(main_sizer)

    def _create_control_panel(self, parent):
        """Создание панели управления"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Кнопки управления
        self.start_all_btn = wx.Button(panel, label="Запуск всех ботов")
        self.stop_all_btn = wx.Button(panel, label="Остановка всех ботов")
        self.add_bot_btn = wx.Button(panel, label="Добавить бота")
        self.settings_btn = wx.Button(panel, label="Настройки")
        self.refresh_btn = wx.Button(panel, label="Обновить")

        # Привязка событий
        self.start_all_btn.Bind(wx.EVT_BUTTON, self.on_start_all)
        self.stop_all_btn.Bind(wx.EVT_BUTTON, self.on_stop_all)
        self.add_bot_btn.Bind(wx.EVT_BUTTON, self.on_add_bot)
        self.settings_btn.Bind(wx.EVT_BUTTON, self.on_settings)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)

        sizer.Add(self.start_all_btn, 0, wx.ALL, 5)
        sizer.Add(self.stop_all_btn, 0, wx.ALL, 5)
        sizer.Add(self.add_bot_btn, 0, wx.ALL, 5)
        sizer.Add(self.settings_btn, 0, wx.ALL, 5)
        sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        sizer.AddStretchSpacer(1)

        # Информация о системе
        self.system_info = wx.StaticText(panel, label="Ботов: 0 | Запущено: 0")
        sizer.Add(self.system_info, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def _create_status_panel(self, parent):
        """Создание панели статуса ботов"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Список ботов
        self.bot_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.bot_list.InsertColumn(0, "Бот", width=150)
        self.bot_list.InsertColumn(1, "Тип", width=100)
        self.bot_list.InsertColumn(2, "Статус", width=150)
        self.bot_list.InsertColumn(3, "Действие", width=200)
        self.bot_list.InsertColumn(4, "Успешно", width=80)
        self.bot_list.InsertColumn(5, "Ошибки", width=80)
        self.bot_list.InsertColumn(6, "Капчи", width=80)
        self.bot_list.InsertColumn(7, "Время цикла", width=100)

        # Привязка контекстного меню
        self.bot_list.Bind(wx.EVT_CONTEXT_MENU, self.on_bot_context_menu)

        sizer.Add(self.bot_list, 1, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def _create_bot_control_panel(self, parent):
        """Создание панели управления выбранным ботом"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Детальная информация о боте
        self.bot_details = wx.StaticText(panel, label="Выберите бота для управления (ПКМ для дополнительных опций)")
        sizer.Add(self.bot_details, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        panel.SetSizer(sizer)
        return panel

    def _create_menu(self):
        """Создание меню"""
        menubar = wx.MenuBar()

        # Меню Файл
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "Выход", "Выход из приложения")
        menubar.Append(file_menu, "&Файл")

        # Меню Боты
        bot_menu = wx.Menu()
        self.add_bot_menu = bot_menu.Append(wx.ID_ADD, "Добавить бота", "Добавить нового бота")
        self.import_bots_menu = bot_menu.Append(wx.ID_OPEN, "Импорт ботов", "Импорт конфигурации ботов")
        self.export_bots_menu = bot_menu.Append(wx.ID_SAVE, "Экспорт ботов", "Экспорт конфигурации ботов")
        menubar.Append(bot_menu, "&Боты")

        # Меню Настройки
        settings_menu = wx.Menu()
        self.general_settings = settings_menu.Append(wx.ID_PREFERENCES, "Общие настройки", "Настройки приложения")
        self.captcha_settings = settings_menu.Append(wx.ID_ANY, "Настройки капчи", "Настройки сервиса капчи")
        self.browser_settings = settings_menu.Append(wx.ID_ANY, "Настройки браузера", "Настройки браузера")
        menubar.Append(settings_menu, "&Настройки")

        # Меню Помощь
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "О программе", "Информация о программе")
        menubar.Append(help_menu, "&Помощь")

        self.SetMenuBar(menubar)

        # Привязка событий меню
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_add_bot, self.add_bot_menu)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

    def _setup_async(self):
        """Настройка асинхронной работы"""
        self.async_thread = threading.Thread(target=self._async_loop, daemon=True)
        self.async_thread.start()

    def _async_loop(self):
        """Асинхронный цикл для работы с ботами"""
        self.loop = asyncio.new_event_loop()  # Сохраняем ссылку на loop
        asyncio.set_event_loop(self.loop)

        async def async_init():
            self.config_manager = ConfigManager()
            self.bot_manager = BotManager(self.config_manager)
            await self.bot_manager.initialize()
            self.running = True

            # Запуск обновления интерфейса
            while self.running:
                await self._update_ui()
                await asyncio.sleep(2)

        try:
            self.loop.run_until_complete(async_init())
        except Exception as e:
            logger.error(f"Ошибка в асинхронном цикле: {e}")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _update_ui(self):
        """Обновление пользовательского интерфейса"""
        if not self.bot_manager:
            return

        # Получение статусов ботов
        statuses = self.bot_manager.get_all_bot_statuses()

        # Обновление в основном потоке WxPython
        wx.CallAfter(self._update_bot_list, statuses)
        wx.CallAfter(self._update_system_info)

    def _update_bot_list(self, statuses: List[Dict[str, Any]]):
        """Обновление списка ботов"""
        self.bot_list.DeleteAllItems()
        self.bot_statuses = {}

        for status in statuses:
            idx = self.bot_list.InsertItem(self.bot_list.GetItemCount(), status["name"])

            bot_type = status.get("type", "Unknown")
            template = status.get("template", "")
            if template and template != "N/A":
                bot_type = f"Шаблон: {template}"

            self.bot_list.SetItem(idx, 1, bot_type)
            self.bot_list.SetItem(idx, 2, status["status"].value)
            self.bot_list.SetItem(idx, 3, status["stats"].current_action)
            self.bot_list.SetItem(idx, 4, str(status["stats"].success_count))
            self.bot_list.SetItem(idx, 5, str(status["stats"].failure_count))
            self.bot_list.SetItem(idx, 6, str(status["stats"].captchas_solved))
            self.bot_list.SetItem(idx, 7, f"{status['stats'].avg_cycle_time:.1f}с")

            # Сохранение статуса для быстрого доступа
            self.bot_statuses[status["name"]] = status

    def _update_system_info(self):
        """Обновление системной информации"""
        if not self.bot_manager:
            return

        total_bots = self.bot_manager.get_bot_count()
        running_bots = self.bot_manager.get_running_bot_count()

        self.system_info.SetLabel(f"Ботов: {total_bots} | Запущено: {running_bots}")
        self.SetStatusText(f"Всего ботов: {total_bots}, запущено: {running_bots}")

    def _run_async_coroutine(self, coro):
        """Безопасный запуск асинхронной корутины"""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    def on_bot_context_menu(self, event):
        """Контекстное меню для бота (ПКМ)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            return

        bot_name = self.bot_list.GetItemText(selected)
        bot_status = self.bot_statuses.get(bot_name)
        if not bot_status:
            return

        # Создание контекстного меню
        menu = wx.Menu()

        # Основные операции
        start_item = menu.Append(wx.ID_ANY, "Запуск бота")
        stop_item = menu.Append(wx.ID_ANY, "Остановка бота")
        restart_item = menu.Append(wx.ID_ANY, "Перезапуск бота")
        menu.AppendSeparator()

        # Запуск с видимым браузером
        start_visible_item = menu.Append(wx.ID_ANY, "Запуск с видимым браузером")
        menu.AppendSeparator()

        # Дополнительные операции
        edit_item = menu.Append(wx.ID_ANY, "Редактировать бота")
        delete_item = menu.Append(wx.ID_ANY, "Удалить бота")
        menu.AppendSeparator()

        # Информация
        info_item = menu.Append(wx.ID_ANY, "Информация о боте")

        # Привязка событий
        self.Bind(wx.EVT_MENU, lambda e: self.on_start_bot_specific(bot_name), start_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_stop_bot_specific(bot_name), stop_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_restart_bot_specific(bot_name), restart_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_start_bot_visible(bot_name), start_visible_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_edit_bot_specific(bot_name), edit_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_delete_bot_specific(bot_name), delete_item)
        self.Bind(wx.EVT_MENU, lambda e: self.on_show_bot_info(bot_name, bot_status), info_item)

        # Показ меню
        self.bot_list.PopupMenu(menu)
        menu.Destroy()

    def on_start_bot_specific(self, bot_name: str):
        """Запуск конкретного бота"""

        async def start():
            await self.bot_manager.start_bot(bot_name)

        self._run_async_coroutine(start())
        logger.info(f"Запуск бота: {bot_name}")

    def on_stop_bot_specific(self, bot_name: str):
        """Остановка конкретного бота"""

        async def stop():
            await self.bot_manager.stop_bot(bot_name)

        self._run_async_coroutine(stop())
        logger.info(f"Остановка бота: {bot_name}")

    def on_restart_bot_specific(self, bot_name: str):
        """Перезапуск конкретного бота"""

        async def restart():
            await self.bot_manager.restart_bot(bot_name)

        self._run_async_coroutine(restart())
        logger.info(f"Перезапуск бота: {bot_name}")

    def on_start_bot_visible(self, bot_name: str):
        """Запуск бота с видимым браузером (headless: False)"""

        async def start_visible():
            # Временное изменение конфигурации браузера для этого запуска
            original_config = self.config_manager.data.get('browser', {}).copy()

            # Устанавливаем headless: false для видимого браузера
            if 'browser' not in self.config_manager.data:
                self.config_manager.data['browser'] = {}
            self.config_manager.data['browser']['headless'] = False

            try:
                await self.bot_manager.start_bot(bot_name)
                logger.info(f"Запуск бота {bot_name} с видимым браузером")
            finally:
                # Восстанавливаем оригинальную конфигурацию
                self.config_manager.data['browser'] = original_config

        self._run_async_coroutine(start_visible())

    def on_edit_bot_specific(self, bot_name: str):
        """Редактирование конкретного бота"""
        if self.config_manager:
            dlg = EditBotDialog(self, self.config_manager, bot_name)
            if dlg.ShowModal() == wx.ID_OK:
                # Перезагрузка ботов после редактирования
                async def reload():
                    await self.bot_manager.reload_bots()

                self._run_async_coroutine(reload())
            dlg.Destroy()
        else:
            wx.MessageBox("Конфигурационный менеджер не инициализирован",
                          "Ошибка", wx.OK | wx.ICON_ERROR)

    def on_delete_bot_specific(self, bot_name: str):
        """Удаление конкретного бота"""
        result = wx.MessageBox(f"Вы уверены, что хотите удалить бота '{bot_name}'?",
                               "Подтверждение удаления",
                               wx.YES_NO | wx.ICON_QUESTION)

        if result == wx.YES:
            async def delete_bot():
                # Удаляем бота из конфигурации
                if "bots" in self.config_manager.bot_data:
                    if bot_name in self.config_manager.bot_data["bots"]:
                        del self.config_manager.bot_data["bots"][bot_name]
                        self.config_manager.save_bot_config()

                        # Перезагружаем ботов
                        await self.bot_manager.reload_bots()
                        logger.info(f"Бот {bot_name} удален")

            self._run_async_coroutine(delete_bot())

    def on_show_bot_info(self, bot_name: str, bot_status: Dict[str, Any]):
        """Показать информацию о боте"""
        info_text = f"""
Информация о боте: {bot_name}

Тип: {bot_status.get('type', 'Unknown')}
Шаблон: {bot_status.get('template', 'N/A')}
Статус: {bot_status['status'].value}
Запущен: {'Да' if bot_status['is_running'] else 'Нет'}
Включен: {'Да' if bot_status['enabled'] else 'Нет'}

Статистика:
- Успешных операций: {bot_status['stats'].success_count}
- Ошибок: {bot_status['stats'].failure_count}
- Решено капч: {bot_status['stats'].captchas_solved}
- Среднее время цикла: {bot_status['stats'].avg_cycle_time:.1f}с
- Текущее действие: {bot_status['stats'].current_action}
"""
        if bot_status['stats'].last_error:
            info_text += f"\nПоследняя ошибка: {bot_status['stats'].last_error}"

        wx.MessageBox(info_text, f"Информация о боте: {bot_name}", wx.OK | wx.ICON_INFORMATION)

    # Обработчики событий для кнопок (оставлены для обратной совместимости)
    def on_start_all(self, event):
        """Запуск всех ботов"""

        async def start():
            await self.bot_manager.start_all()

        self._run_async_coroutine(start())

    def on_stop_all(self, event):
        """Остановка всех ботов"""

        async def stop():
            await self.bot_manager.stop_all()

        self._run_async_coroutine(stop())

    def on_start_bot(self, event):
        """Запуск выбранного бота (для обратной совместимости)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Выберите бота для запуска", "Внимание", wx.OK | wx.ICON_WARNING)
            return

        bot_name = self.bot_list.GetItemText(selected)
        self.on_start_bot_specific(bot_name)

    def on_stop_bot(self, event):
        """Остановка выбранного бота (для обратной совместимости)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Выберите бота для остановки", "Внимание", wx.OK | wx.ICON_WARNING)
            return

        bot_name = self.bot_list.GetItemText(selected)
        self.on_stop_bot_specific(bot_name)

    def on_restart_bot(self, event):
        """Перезапуск выбранного бота (для обратной совместимости)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Выберите бота для перезапуска", "Внимание", wx.OK | wx.ICON_WARNING)
            return

        bot_name = self.bot_list.GetItemText(selected)
        self.on_restart_bot_specific(bot_name)

    def on_add_bot(self, event):
        """Открытие диалога добавления бота"""
        if self.config_manager:
            dlg = AddBotDialog(self, self.config_manager)
            if dlg.ShowModal() == wx.ID_OK:
                # Перезагрузка ботов после добавления нового
                async def reload():
                    await self.bot_manager.reload_bots()

                self._run_async_coroutine(reload())
            dlg.Destroy()
        else:
            wx.MessageBox("Конфигурационный менеджер не инициализирован",
                          "Ошибка", wx.OK | wx.ICON_ERROR)

    def on_edit_bot(self, event):
        """Редактирование выбранного бота (для обратной совместимости)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Выберите бота для редактирования", "Внимание", wx.OK | wx.ICON_WARNING)
            return

        bot_name = self.bot_list.GetItemText(selected)
        self.on_edit_bot_specific(bot_name)

    def on_delete_bot(self, event):
        """Удаление выбранного бота (для обратной совместимости)"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            wx.MessageBox("Выберите бота для удаления", "Внимание", wx.OK | wx.ICON_WARNING)
            return

        bot_name = self.bot_list.GetItemText(selected)
        self.on_delete_bot_specific(bot_name)

    def on_settings(self, event):
        """Открытие диалога настроек"""
        if self.config_manager:
            dlg = SettingsDialog(self, self.config_manager)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            wx.MessageBox("Конфигурационный менеджер не инициализирован",
                          "Ошибка", wx.OK | wx.ICON_ERROR)

    def on_refresh(self, event):
        """Обновление статуса"""
        self._update_system_info()

    def on_about(self, event):
        """О программе"""
        info = wx.adv.AboutDialogInfo()
        info.SetName("Crypto Bot Manager")
        info.SetVersion("2.0")
        info.SetDescription("Автоматизация работы с faucet-сайтами\n\nКонсольная версия с графическим интерфейсом")
        info.SetCopyright("(C) 2024")

        wx.adv.AboutBox(info)

    def on_exit(self, event):
        """Выход из приложения"""
        self.running = False

        # Корректное завершение асинхронного цикла
        async def shutdown():
            if self.bot_manager:
                await self.bot_manager.shutdown()

        if self.loop and not self.loop.is_closed():
            # Запускаем shutdown в асинхронном потоке
            future = asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            try:
                future.result(timeout=10)  # Ждем завершения до 10 секунд
            except Exception as e:
                logger.error(f"Ошибка при завершении работы: {e}")

        self.Close()


class BotManagerApp(wx.App):
    def OnInit(self):
        self.frame = BotManagerFrame()
        return True


if __name__ == "__main__":
    app = BotManagerApp()
    app.MainLoop()
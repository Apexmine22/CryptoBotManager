# main.py
"""
Главное окно приложения - исправленная версия
"""

import wx
import wx.adv
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Any

from core.config_manager import ConfigManager
from core.bot_manager import BotManager
from utils.logger import logger
from ui.modern_theme import ModernTheme, ModernPanel
from ui.AddBot import AddBotDialog
from ui.EditBotDialog import EditBotDialog
from ui.settings import SettingsDialog


class ModernStatusPanel(ModernPanel):
    """Современная панель статуса ботов"""

    def __init__(self, parent):
        super().__init__(parent)
        self.bot_statuses = {}
        self.parent = parent  # Сохраняем ссылку на родительское окно
        self._init_ui()

    def _init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Заголовок
        title = ModernTheme.create_section_title(self, "📊 Статус ботов")
        sizer.Add(title, 0, wx.ALL, 10)

        # Список ботов
        self.bot_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL)
        self.bot_list.InsertColumn(0, "🤖 Бот", width=150)
        self.bot_list.InsertColumn(1, "🔧 Тип", width=100)
        self.bot_list.InsertColumn(2, "📊 Статус", width=150)
        self.bot_list.InsertColumn(3, "⚡ Действие", width=200)
        self.bot_list.InsertColumn(4, "✅ Успешно", width=80)
        self.bot_list.InsertColumn(5, "❌ Ошибки", width=80)
        self.bot_list.InsertColumn(6, "🧩 Капчи", width=80)
        self.bot_list.InsertColumn(7, "⏱️ Время", width=100)

        ModernTheme.apply_theme(self.bot_list)

        # Привязка контекстного меню
        self.bot_list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)

        sizer.Add(self.bot_list, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)

    def on_context_menu(self, event):
        """Контекстное меню для бота"""
        selected = self.bot_list.GetFirstSelected()
        if selected == -1:
            return

        bot_name = self.bot_list.GetItemText(selected)
        bot_status = self.bot_statuses.get(bot_name)
        if not bot_status:
            return

        menu = wx.Menu()

        # Опции меню
        start_item = menu.Append(wx.ID_ANY, "🚀 Запуск бота")
        stop_item = menu.Append(wx.ID_ANY, "🛑 Остановка бота")
        restart_item = menu.Append(wx.ID_ANY, "🔄 Перезапуск бота")
        menu.AppendSeparator()
        edit_item = menu.Append(wx.ID_ANY, "✏️ Редактировать бота")
        delete_item = menu.Append(wx.ID_ANY, "🗑️ Удалить бота")
        menu.AppendSeparator()
        info_item = menu.Append(wx.ID_ANY, "ℹ️ Информация о боте")

        # Привязка событий к родительскому окну
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_start_bot_specific(bot_name), start_item)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_stop_bot_specific(bot_name), stop_item)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_restart_bot_specific(bot_name), restart_item)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_edit_bot_specific(bot_name), edit_item)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_delete_bot_specific(bot_name), delete_item)
        self.Bind(wx.EVT_MENU, lambda e: self.parent.on_show_bot_info(bot_name, bot_status), info_item)

        self.bot_list.PopupMenu(menu)
        menu.Destroy()

    def update_bot_list(self, statuses: List[Dict[str, Any]]):
        """Обновление списка ботов"""
        self.bot_list.DeleteAllItems()
        self.bot_statuses = {}

        for status in statuses:
            idx = self.bot_list.InsertItem(self.bot_list.GetItemCount(), status["name"])

            bot_type = status.get("type", "Unknown")
            template = status.get("template", "")
            if template and template != "N/A":
                bot_type = f"📁 {template}"
            else:
                bot_type = "🔧 Универсальный"

            self.bot_list.SetItem(idx, 1, bot_type)
            self.bot_list.SetItem(idx, 2, status["status"].value)
            self.bot_list.SetItem(idx, 3, status["stats"].current_action)
            self.bot_list.SetItem(idx, 4, str(status["stats"].success_count))
            self.bot_list.SetItem(idx, 5, str(status["stats"].failure_count))
            self.bot_list.SetItem(idx, 6, str(status["stats"].captchas_solved))
            self.bot_list.SetItem(idx, 7, f"{status['stats'].avg_cycle_time:.1f}с")

            self.bot_statuses[status["name"]] = status


class ModernControlPanel(ModernPanel):
    """Современная панель управления"""

    def __init__(self, parent, on_start_all, on_stop_all, on_add_bot, on_settings, on_refresh):
        super().__init__(parent)
        self.on_start_all = on_start_all
        self.on_stop_all = on_stop_all
        self.on_add_bot = on_add_bot
        self.on_settings = on_settings
        self.on_refresh = on_refresh
        self._init_ui()

    def _init_ui(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Кнопки управления
        self.start_btn = ModernTheme.create_modern_button(self, "🚀 Запуск всех", 'success')
        self.stop_btn = ModernTheme.create_modern_button(self, "🛑 Остановка всех", 'error')
        self.add_btn = ModernTheme.create_modern_button(self, "➕ Добавить бота", 'accent')
        self.settings_btn = ModernTheme.create_modern_button(self, "⚙️ Настройки", 'secondary')
        self.refresh_btn = ModernTheme.create_modern_button(self, "🔄 Обновить", 'primary')

        # Привязка событий
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_all)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_all)
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add_bot)
        self.settings_btn.Bind(wx.EVT_BUTTON, self.on_settings)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)

        sizer.Add(self.start_btn, 0, wx.ALL, 5)
        sizer.Add(self.stop_btn, 0, wx.ALL, 5)
        sizer.Add(self.add_btn, 0, wx.ALL, 5)
        sizer.Add(self.settings_btn, 0, wx.ALL, 5)
        sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        sizer.AddStretchSpacer(1)

        # Информация о системе
        self.system_info = ModernTheme.create_status_label(self, "🤖 Ботов: 0 | 🚀 Запущено: 0")
        sizer.Add(self.system_info, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 10)

        self.SetSizer(sizer)

    def update_system_info(self, total_bots: int, running_bots: int):
        """Обновление системной информации"""
        self.system_info.SetLabel(f"🤖 Ботов: {total_bots} | 🚀 Запущено: {running_bots}")


class BotManagerFrame(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title="Crypto Bot Manager v4.1", size=(1400, 900))

        self.config_manager = None
        self.bot_manager = None
        self.async_thread = None
        self.running = False
        self.loop = None

        ModernTheme.apply_theme(self)
        self._init_ui()
        self._create_modern_menu()
        self._setup_async()

        self.Center()
        self.Show()

    def _init_ui(self):
        """Инициализация современного UI"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Панель управления
        self.control_panel = ModernControlPanel(
            panel,
            self.on_start_all,
            self.on_stop_all,
            self.on_add_bot,
            self.on_settings,
            self.on_refresh
        )
        main_sizer.Add(self.control_panel, 0, wx.EXPAND | wx.ALL, 5)

        # Панель статуса
        self.status_panel = ModernStatusPanel(panel)
        self.status_panel.parent = self  # Передаем ссылку на родительское окно
        main_sizer.Add(self.status_panel, 1, wx.EXPAND | wx.ALL, 5)

        # Современный статус бар
        self.CreateStatusBar()
        self.status_bar = self.GetStatusBar()
        self.status_bar.SetBackgroundColour(ModernTheme.COLORS['primary'])
        self.status_bar.SetForegroundColour(ModernTheme.COLORS['surface'])
        self.SetStatusText("✅ Готов к работе")

        panel.SetSizer(main_sizer)

    def _create_modern_menu(self):
        """Создание современного меню"""
        menubar = wx.MenuBar()

        # Меню Файл
        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "Выход\tCtrl+Q", "Выход из приложения")
        menubar.Append(file_menu, "&Файл")

        # Меню Боты
        bot_menu = wx.Menu()
        self.add_bot_menu = bot_menu.Append(wx.ID_ADD, "Добавить бота\tCtrl+N", "Добавить нового бота")
        menubar.Append(bot_menu, "&Боты")

        # Меню Настройки
        settings_menu = wx.Menu()
        self.general_settings = settings_menu.Append(wx.ID_PREFERENCES, "Настройки\tCtrl+,", "Настройки приложения")
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
        self.Bind(wx.EVT_MENU, self.on_settings, self.general_settings)

    def _setup_async(self):
        """Настройка асинхронной работы"""
        self.async_thread = threading.Thread(target=self._async_loop, daemon=True)
        self.async_thread.start()

    def _async_loop(self):
        """Асинхронный цикл для работы с ботами"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def async_init():
            try:
                self.config_manager = ConfigManager()
                self.bot_manager = BotManager(self.config_manager)
                await self.bot_manager.initialize()
                self.running = True
                logger.success("✅ Приложение инициализировано")

                # Запуск обновления интерфейса
                while self.running:
                    await self._update_ui()
                    await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации: {e}")
                self.running = False

        try:
            self.loop.run_until_complete(async_init())
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()

    async def _update_ui(self):
        """Обновление пользовательского интерфейса"""
        if not self.bot_manager or not self.running:
            return

        try:
            statuses = self.bot_manager.get_all_bot_statuses()

            wx.CallAfter(self.status_panel.update_bot_list, statuses)

            total_bots = self.bot_manager.get_bot_count()
            running_bots = self.bot_manager.get_running_bot_count()
            wx.CallAfter(self.control_panel.update_system_info, total_bots, running_bots)
            wx.CallAfter(self.SetStatusText, f"🤖 Ботов: {total_bots} | 🚀 Запущено: {running_bots}")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления UI: {e}")

    def _run_async_coroutine(self, coro):
        """Безопасный запуск асинхронной корутины"""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(coro, self.loop)

    # Обработчики событий для контекстного меню
    def on_start_bot_specific(self, bot_name: str):
        async def start():
            await self.bot_manager.start_bot(bot_name)

        self._run_async_coroutine(start())

    def on_stop_bot_specific(self, bot_name: str):
        async def stop():
            await self.bot_manager.stop_bot(bot_name)

        self._run_async_coroutine(stop())

    def on_restart_bot_specific(self, bot_name: str):
        async def restart():
            await self.bot_manager.restart_bot(bot_name)

        self._run_async_coroutine(restart())

    def on_edit_bot_specific(self, bot_name: str):
        if self.config_manager:
            dlg = EditBotDialog(self, self.config_manager, bot_name)
            if dlg.ShowModal() == wx.ID_OK:
                async def reload():
                    await self.bot_manager.reload_bots()

                self._run_async_coroutine(reload())
            dlg.Destroy()

    def on_delete_bot_specific(self, bot_name: str):
        result = wx.MessageBox(f"Вы уверены, что хотите удалить бота '{bot_name}'?",
                               "Подтверждение удаления", wx.YES_NO | wx.ICON_QUESTION)
        if result == wx.YES:
            async def delete_bot():
                if "bots" in self.config_manager.bot_data and bot_name in self.config_manager.bot_data["bots"]:
                    del self.config_manager.bot_data["bots"][bot_name]
                    self.config_manager.save_bot_config()
                    await self.bot_manager.reload_bots()
                    logger.info(f"🗑️ Бот {bot_name} удален")

            self._run_async_coroutine(delete_bot())

    def on_show_bot_info(self, bot_name: str, bot_status: Dict[str, Any]):
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

    # Основные обработчики событий
    def on_start_all(self, event):
        async def start():
            await self.bot_manager.start_all()

        self._run_async_coroutine(start())

    def on_stop_all(self, event):
        async def stop():
            await self.bot_manager.stop_all()

        self._run_async_coroutine(stop())

    def on_add_bot(self, event):
        if self.config_manager:
            dlg = AddBotDialog(self, self.config_manager)
            if dlg.ShowModal() == wx.ID_OK:
                async def reload():
                    await self.bot_manager.reload_bots()

                self._run_async_coroutine(reload())
            dlg.Destroy()
        else:
            self._show_error("Конфигурационный менеджер не инициализирован")

    def on_settings(self, event):
        if self.config_manager:
            dlg = SettingsDialog(self, self.config_manager)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            self._show_error("Конфигурационный менеджер не инициализирован")

    def on_refresh(self, event):
        async def refresh():
            if self.bot_manager:
                total_bots = self.bot_manager.get_bot_count()
                running_bots = self.bot_manager.get_running_bot_count()
                wx.CallAfter(self.control_panel.update_system_info, total_bots, running_bots)

        self._run_async_coroutine(refresh())

    def on_about(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName("Crypto Bot Manager")
        info.SetVersion("4.1")
        info.SetDescription("Современная автоматизация работы с faucet-сайтами\n\n"
                            "✨ Современный интерфейс\n"
                            "🚀 Высокая производительность\n"
                            "🔧 Гибкая настройка ботов")
        info.SetCopyright("(C) 2024")
        info.SetDevelopers(["Crypto Bot Manager Team"])

        wx.adv.AboutBox(info)

    def on_exit(self, event):
        """Корректный выход из приложения"""
        self.running = False

        async def shutdown():
            if self.bot_manager:
                await self.bot_manager.shutdown()
            await asyncio.sleep(1)

        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            try:
                future.result(timeout=10)
            except Exception as e:
                logger.error(f"⚠️ Ошибка при завершении: {e}")
            finally:
                self.loop.call_soon_threadsafe(self.loop.stop)

        self.Destroy()

    def _show_error(self, message: str):
        """Показать сообщение об ошибке"""
        dlg = wx.MessageDialog(self, message, "Ошибка", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()


class ModernApp(wx.App):
    def OnInit(self):
        self.frame = BotManagerFrame()
        self.SetTopWindow(self.frame)
        return True


if __name__ == "__main__":
    app = ModernApp()
    app.MainLoop()
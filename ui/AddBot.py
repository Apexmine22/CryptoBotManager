import wx
import wx.adv
from pathlib import Path


class AddBotDialog(wx.Dialog):
    def __init__(self, parent, config_manager):
        super().__init__(parent, title="Добавить бота", size=(600, 700))
        self.config_manager = config_manager
        self.bot_config = {}

        self._init_ui()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Создание вкладок
        notebook = wx.Notebook(panel)

        # Основные настройки
        basic_tab = self._create_basic_tab(notebook)
        notebook.AddPage(basic_tab, "Основные")

        # Настройки авторизации
        auth_tab = self._create_auth_tab(notebook)
        notebook.AddPage(auth_tab, "Авторизация")

        # Настройки селекторов
        selectors_tab = self._create_selectors_tab(notebook)
        notebook.AddPage(selectors_tab, "Селекторы")

        # Настройки навигации
        navigation_tab = self._create_navigation_tab(notebook)
        notebook.AddPage(navigation_tab, "Навигация")

        # Настройки бота
        settings_tab = self._create_settings_tab(notebook)
        notebook.AddPage(settings_tab, "Настройки")

        # Настройки капчи
        captcha_tab = self._create_captcha_tab(notebook)
        notebook.AddPage(captcha_tab, "Капча")

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки сохранения/отмены
        button_sizer = self._create_button_sizer(panel)
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        panel.SetSizer(main_sizer)

    def _create_basic_tab(self, parent):
        """Создание вкладки основных настроек"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Название бота
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        name_label = wx.StaticText(panel, label="Название бота:*")
        self.name_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        name_sizer.Add(name_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        name_sizer.Add(self.name_text, 1, wx.EXPAND)

        # URL сайта
        url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_label = wx.StaticText(panel, label="URL сайта:*")
        self.url_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        url_sizer.Add(url_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        url_sizer.Add(self.url_text, 1, wx.EXPAND)

        # Тип бота
        type_sizer = wx.BoxSizer(wx.HORIZONTAL)
        type_label = wx.StaticText(panel, label="Тип бота:")
        self.bot_type = wx.Choice(panel, choices=["Универсальный", "Шаблонный"])
        self.bot_type.SetSelection(0)
        type_sizer.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        type_sizer.Add(self.bot_type, 1, wx.EXPAND)

        # Выбор шаблона (только для шаблонных ботов)
        self.template_sizer = wx.BoxSizer(wx.HORIZONTAL)
        template_label = wx.StaticText(panel, label="Шаблон:")
        self.template_choice = wx.Choice(panel, choices=[])
        self.template_sizer.Add(template_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.template_sizer.Add(self.template_choice, 1, wx.EXPAND)
        self.template_sizer.ShowItems(False)

        # Включен ли бот
        self.enabled_checkbox = wx.CheckBox(panel, label="Бот включен")
        self.enabled_checkbox.SetValue(True)

        sizer.Add(name_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(url_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(type_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.template_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.enabled_checkbox, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.AddStretchSpacer(1)

        # Информация
        info_text = wx.StaticText(panel, label="* - обязательные поля")
        info_text.SetForegroundColour(wx.Colour(100, 100, 100))
        sizer.Add(info_text, 0, wx.ALIGN_CENTER)

        # Загрузка доступных шаблонов
        self._load_templates()

        # Привязка событий
        self.bot_type.Bind(wx.EVT_CHOICE, self.on_bot_type_changed)

        panel.SetSizer(sizer)
        return panel

    def _create_auth_tab(self, parent):
        """Создание вкладки авторизации"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Email
        email_sizer = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(panel, label="Email:*")
        self.email_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        email_sizer.Add(email_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        email_sizer.Add(self.email_text, 1, wx.EXPAND)

        # Password
        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_label = wx.StaticText(panel, label="Пароль:*")
        self.password_text = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_LEFT)
        password_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        password_sizer.Add(self.password_text, 1, wx.EXPAND)

        sizer.Add(email_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(password_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.AddStretchSpacer(1)

        # Использовать настройки по умолчанию
        self.use_default_auth = wx.CheckBox(panel, label="Использовать настройки авторизации по умолчанию")
        self.use_default_auth.Bind(wx.EVT_CHECKBOX, self.on_use_default_auth)
        sizer.Add(self.use_default_auth, 0, wx.EXPAND)

        panel.SetSizer(sizer)
        return panel

    def _create_selectors_tab(self, parent):
        """Создание вкладки селекторов"""
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(5, 5)

        # Селекторы логина
        login_label = wx.StaticText(panel, label="Селекторы логина:")
        login_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(login_label, pos=(0, 0), span=(1, 2), flag=wx.EXPAND | wx.BOTTOM, border=10)

        # Поля формы логина
        sizer.Add(wx.StaticText(panel, label="Поле email:"), pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.login_email_field = wx.TextCtrl(panel)
        sizer.Add(self.login_email_field, pos=(1, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Поле пароля:"), pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.login_password_field = wx.TextCtrl(panel)
        sizer.Add(self.login_password_field, pos=(2, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Кнопка логина:"), pos=(3, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.login_button = wx.TextCtrl(panel)
        sizer.Add(self.login_button, pos=(3, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Ссылка логина:"), pos=(4, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.login_link = wx.TextCtrl(panel)
        sizer.Add(self.login_link, pos=(4, 1), flag=wx.EXPAND)

        # Селекторы действий
        action_label = wx.StaticText(panel, label="Селекторы действий:")
        action_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(action_label, pos=(5, 0), span=(1, 2), flag=wx.EXPAND | wx.TOP | wx.BOTTOM, border=10)

        sizer.Add(wx.StaticText(panel, label="Кнопка Claim:"), pos=(6, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.claim_button = wx.TextCtrl(panel)
        sizer.Add(self.claim_button, pos=(6, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Кнопка Roll:"), pos=(7, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.roll_button = wx.TextCtrl(panel)
        sizer.Add(self.roll_button, pos=(7, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Кнопка Faucet:"), pos=(8, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.faucet_button = wx.TextCtrl(panel)
        sizer.Add(self.faucet_button, pos=(8, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Текст баланса:"), pos=(9, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.balance_text = wx.TextCtrl(panel)
        sizer.Add(self.balance_text, pos=(9, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Индикатор успеха:"), pos=(10, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.success_indicator = wx.TextCtrl(panel)
        sizer.Add(self.success_indicator, pos=(10, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Индикатор ошибки:"), pos=(11, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.error_indicator = wx.TextCtrl(panel)
        sizer.Add(self.error_indicator, pos=(11, 1), flag=wx.EXPAND)

        sizer.AddGrowableCol(1)
        panel.SetSizer(sizer)
        return panel

    def _create_navigation_tab(self, parent):
        """Создание вкладки навигации"""
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(5, 5)

        sizer.Add(wx.StaticText(panel, label="URL логина:"), pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.login_url = wx.TextCtrl(panel)
        sizer.Add(self.login_url, pos=(0, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="URL дашборда:"), pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.dashboard_url = wx.TextCtrl(panel)
        sizer.Add(self.dashboard_url, pos=(1, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="URL Claim:"), pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.claim_url = wx.TextCtrl(panel)
        sizer.Add(self.claim_url, pos=(2, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="URL Faucet:"), pos=(3, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.faucet_url = wx.TextCtrl(panel)
        sizer.Add(self.faucet_url, pos=(3, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="URL профиля:"), pos=(4, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.profile_url = wx.TextCtrl(panel)
        sizer.Add(self.profile_url, pos=(4, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="URL баланса:"), pos=(5, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.balance_url = wx.TextCtrl(panel)
        sizer.Add(self.balance_url, pos=(5, 1), flag=wx.EXPAND)

        sizer.AddGrowableCol(1)
        panel.SetSizer(sizer)
        return panel

    def _create_settings_tab(self, parent):
        """Создание вкладки настроек бота"""
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(5, 5)

        # Задержки
        sizer.Add(wx.StaticText(panel, label="Задержка между циклами (сек):"), pos=(0, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.cycle_delay = wx.SpinCtrl(panel, min=30, max=3600, initial=300)
        sizer.Add(self.cycle_delay, pos=(0, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Задержка между действиями (сек):"), pos=(1, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.currency_delay = wx.SpinCtrl(panel, min=1, max=60, initial=3)
        sizer.Add(self.currency_delay, pos=(1, 1), flag=wx.EXPAND)

        # Таймауты
        sizer.Add(wx.StaticText(panel, label="Таймаут ожидания (сек):"), pos=(2, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.wait_timeout = wx.SpinCtrl(panel, min=10, max=300, initial=30)
        sizer.Add(self.wait_timeout, pos=(2, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Максимум попыток:"), pos=(3, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.max_retries = wx.SpinCtrl(panel, min=1, max=10, initial=3)
        sizer.Add(self.max_retries, pos=(3, 1), flag=wx.EXPAND)

        # Ошибки
        sizer.Add(wx.StaticText(panel, label="Макс. ошибок подряд:"), pos=(4, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.max_consecutive_errors = wx.SpinCtrl(panel, min=1, max=20, initial=5)
        sizer.Add(self.max_consecutive_errors, pos=(4, 1), flag=wx.EXPAND)

        # Случайные задержки
        self.random_delays = wx.CheckBox(panel, label="Случайные задержки")
        self.random_delays.SetValue(True)
        sizer.Add(self.random_delays, pos=(5, 0), span=(1, 2), flag=wx.EXPAND | wx.BOTTOM, border=5)

        sizer.Add(wx.StaticText(panel, label="Мин. задержка (сек):"), pos=(6, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.min_delay = wx.SpinCtrl(panel, min=1, max=10, initial=2)
        sizer.Add(self.min_delay, pos=(6, 1), flag=wx.EXPAND)

        sizer.Add(wx.StaticText(panel, label="Макс. задержка (сек):"), pos=(7, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.max_delay = wx.SpinCtrl(panel, min=2, max=30, initial=5)
        sizer.Add(self.max_delay, pos=(7, 1), flag=wx.EXPAND)

        # Дополнительные опции
        self.screenshot_on_error = wx.CheckBox(panel, label="Скриншот при ошибке")
        self.screenshot_on_error.SetValue(True)
        sizer.Add(self.screenshot_on_error, pos=(8, 0), span=(1, 2), flag=wx.EXPAND | wx.BOTTOM, border=5)

        self.save_cookies = wx.CheckBox(panel, label="Сохранять куки")
        self.save_cookies.SetValue(True)
        sizer.Add(self.save_cookies, pos=(9, 0), span=(1, 2), flag=wx.EXPAND | wx.BOTTOM, border=5)

        self.stop_on_critical_error = wx.CheckBox(panel, label="Останавливать при критической ошибке")
        self.stop_on_critical_error.SetValue(True)
        sizer.Add(self.stop_on_critical_error, pos=(10, 0), span=(1, 2), flag=wx.EXPAND)

        sizer.AddGrowableCol(1)
        panel.SetSizer(sizer)
        return panel

    def _create_captcha_tab(self, parent):
        """Создание вкладки настроек капчи"""
        panel = wx.Panel(parent)
        sizer = wx.GridBagSizer(5, 5)

        # Тип капчи
        sizer.Add(wx.StaticText(panel, label="Тип капчи:"), pos=(0, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.captcha_type = wx.Choice(panel, choices=["auto", "hcaptcha", "antibot", "image", "none"])
        self.captcha_type.SetSelection(0)
        sizer.Add(self.captcha_type, pos=(0, 1), flag=wx.EXPAND)

        # Site key (для hcaptcha)
        sizer.Add(wx.StaticText(panel, label="Site key:"), pos=(1, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.site_key = wx.TextCtrl(panel)
        sizer.Add(self.site_key, pos=(1, 1), flag=wx.EXPAND)

        # URL страницы
        sizer.Add(wx.StaticText(panel, label="URL страницы:"), pos=(2, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.page_url = wx.TextCtrl(panel)
        sizer.Add(self.page_url, pos=(2, 1), flag=wx.EXPAND)

        # Селектор изображения
        sizer.Add(wx.StaticText(panel, label="Селектор изображения:"), pos=(3, 0),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.image_selector = wx.TextCtrl(panel)
        sizer.Add(self.image_selector, pos=(3, 1), flag=wx.EXPAND)

        # Фрейм капчи
        sizer.Add(wx.StaticText(panel, label="Фрейм капчи:"), pos=(4, 0), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                  border=5)
        self.captcha_frame = wx.TextCtrl(panel)
        sizer.Add(self.captcha_frame, pos=(4, 1), flag=wx.EXPAND)

        # Авто-решение
        self.auto_solve = wx.CheckBox(panel, label="Автоматическое решение")
        self.auto_solve.SetValue(True)
        sizer.Add(self.auto_solve, pos=(5, 0), span=(1, 2), flag=wx.EXPAND | wx.BOTTOM, border=5)

        # Повтор при ошибке
        self.retry_on_fail = wx.CheckBox(panel, label="Повторять при ошибке")
        self.retry_on_fail.SetValue(True)
        sizer.Add(self.retry_on_fail, pos=(6, 0), span=(1, 2), flag=wx.EXPAND)

        sizer.AddGrowableCol(1)
        panel.SetSizer(sizer)
        return panel

    def _create_button_sizer(self, parent):
        """Создание панели с кнопками"""
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        save_btn = wx.Button(parent, wx.ID_OK, "Сохранить")
        cancel_btn = wx.Button(parent, wx.ID_CANCEL, "Отмена")

        save_btn.Bind(wx.EVT_BUTTON, self.on_save)

        sizer.Add(save_btn, 0, wx.RIGHT, 10)
        sizer.Add(cancel_btn, 0)

        return sizer

    def _load_templates(self):
        """Загрузка доступных шаблонов"""
        templates = self.config_manager.get_available_templates()
        self.template_choice.Clear()
        self.template_choice.AppendItems(templates)
        if templates:
            self.template_choice.SetSelection(0)

    def on_bot_type_changed(self, event):
        """Обработчик изменения типа бота"""
        is_template = self.bot_type.GetSelection() == 1
        self.template_sizer.ShowItems(is_template)
        self.Layout()

    def on_use_default_auth(self, event):
        """Обработчик использования настроек по умолчанию"""
        use_default = self.use_default_auth.GetValue()
        self.email_text.Enable(not use_default)
        self.password_text.Enable(not use_default)

        if use_default:
            # Заполняем поля значениями по умолчанию
            default_email = self.config_manager.data.get('general', {}).get('default_email', '')
            default_password = self.config_manager.data.get('general', {}).get('default_password', '')
            self.email_text.SetValue(default_email)
            self.password_text.SetValue(default_password)

    def on_save(self, event):
        """Сохранение бота"""
        try:
            # Валидация обязательных полей
            if not self.name_text.GetValue().strip():
                wx.MessageBox("Введите название бота", "Ошибка", wx.OK | wx.ICON_ERROR)
                return

            if not self.url_text.GetValue().strip():
                wx.MessageBox("Введите URL сайта", "Ошибка", wx.OK | wx.ICON_ERROR)
                return

            if not self.email_text.GetValue().strip() or not self.password_text.GetValue().strip():
                wx.MessageBox("Введите email и пароль", "Ошибка", wx.OK | wx.ICON_ERROR)
                return

            # Сбор данных бота
            bot_data = {
                "name": self.name_text.GetValue().strip(),
                "enabled": self.enabled_checkbox.GetValue(),
                "url": self.url_text.GetValue().strip(),
                "email": self.email_text.GetValue().strip(),
                "password": self.password_text.GetValue().strip(),
                "template": self.template_choice.GetStringSelection() if self.bot_type.GetSelection() == 1 else "",
                "cycle_delay": self.cycle_delay.GetValue(),
                "currency_delay": self.currency_delay.GetValue(),
                "max_consecutive_errors": self.max_consecutive_errors.GetValue(),
                "stop_on_critical_error": self.stop_on_critical_error.GetValue(),
                "login_selectors": {
                    "email_field": self.login_email_field.GetValue().strip(),
                    "password_field": self.login_password_field.GetValue().strip(),
                    "login_button": self.login_button.GetValue().strip(),
                    "login_link": self.login_link.GetValue().strip(),
                },
                "action_selectors": {
                    "claim_button": self.claim_button.GetValue().strip(),
                    "roll_button": self.roll_button.GetValue().strip(),
                    "faucet_button": self.faucet_button.GetValue().strip(),
                    "balance_text": self.balance_text.GetValue().strip(),
                    "success_indicator": self.success_indicator.GetValue().strip(),
                    "error_indicator": self.error_indicator.GetValue().strip(),
                },
                "navigation": {
                    "login_url": self.login_url.GetValue().strip(),
                    "dashboard_url": self.dashboard_url.GetValue().strip(),
                    "claim_url": self.claim_url.GetValue().strip(),
                    "faucet_url": self.faucet_url.GetValue().strip(),
                    "profile_url": self.profile_url.GetValue().strip(),
                    "balance_url": self.balance_url.GetValue().strip(),
                },
                "settings": {
                    "wait_timeout": self.wait_timeout.GetValue(),
                    "max_retries": self.max_retries.GetValue(),
                    "screenshot_on_error": self.screenshot_on_error.GetValue(),
                    "save_cookies": self.save_cookies.GetValue(),
                    "random_delays": self.random_delays.GetValue(),
                    "min_delay": self.min_delay.GetValue(),
                    "max_delay": self.max_delay.GetValue(),
                },
                "captcha": {
                    "captcha_type": self.captcha_type.GetStringSelection(),
                    "site_key": self.site_key.GetValue().strip(),
                    "page_url": self.page_url.GetValue().strip(),
                    "image_selector": self.image_selector.GetValue().strip(),
                    "captcha_frame": self.captcha_frame.GetValue().strip(),
                    "auto_solve": self.auto_solve.GetValue(),
                    "retry_on_fail": self.retry_on_fail.GetValue(),
                }
            }

            # Сохранение в конфигурацию
            bot_name = bot_data["name"]
            if "bots" not in self.config_manager.bot_data:
                self.config_manager.bot_data["bots"] = {}

            if bot_name in self.config_manager.bot_data["bots"]:
                result = wx.MessageBox(f"Бот с именем '{bot_name}' уже существует. Перезаписать?",
                                       "Подтверждение", wx.YES_NO | wx.ICON_QUESTION)
                if result != wx.YES:
                    return

            self.config_manager.bot_data["bots"][bot_name] = bot_data
            self.config_manager.save_bot_config()

            wx.MessageBox(f"Бот '{bot_name}' успешно добавлен!", "Успех", wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)

        except Exception as e:
            wx.MessageBox(f"Ошибка при сохранении бота: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)

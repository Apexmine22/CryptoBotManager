import wx
import wx.adv


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, config_manager):
        super().__init__(parent, title="Настройки", size=(500, 400))
        self.config_manager = config_manager
        self.config_data = config_manager.data.copy()

        self._init_ui()
        self._load_current_settings()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса"""
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Создание вкладок
        notebook = wx.Notebook(panel)

        # Вкладка авторизации
        auth_tab = self._create_auth_tab(notebook)
        notebook.AddPage(auth_tab, "Авторизация")

        # Вкладка капчи
        captcha_tab = self._create_captcha_tab(notebook)
        notebook.AddPage(captcha_tab, "Капча")

        # Вкладка браузера
        browser_tab = self._create_browser_tab(notebook)
        notebook.AddPage(browser_tab, "Браузер")

        main_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        # Кнопки сохранения/отмены
        button_sizer = self._create_button_sizer(panel)
        main_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        panel.SetSizer(main_sizer)

    def _create_auth_tab(self, parent):
        """Создание вкладки авторизации"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Email
        email_sizer = wx.BoxSizer(wx.HORIZONTAL)
        email_label = wx.StaticText(panel, label="Email:")
        self.email_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        email_sizer.Add(email_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        email_sizer.Add(self.email_text, 1, wx.EXPAND)

        # Password
        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_label = wx.StaticText(panel, label="Пароль:")
        self.password_text = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_LEFT)
        password_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        password_sizer.Add(self.password_text, 1, wx.EXPAND)

        sizer.Add(email_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(password_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.AddStretchSpacer(1)

        # Информация
        info_text = wx.StaticText(panel, label="Эти настройки используются по умолчанию\nпри создании новых ботов")
        info_text.SetForegroundColour(wx.Colour(100, 100, 100))
        sizer.Add(info_text, 0, wx.ALIGN_CENTER)

        panel.SetSizer(sizer)
        return panel

    def _create_captcha_tab(self, parent):
        """Создание вкладки капчи"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Выбор сервиса капчи
        service_sizer = wx.BoxSizer(wx.HORIZONTAL)
        service_label = wx.StaticText(panel, label="Сервис капчи:")
        self.captcha_service = wx.Choice(panel, choices=["MultiBot", "XEvil"])
        service_sizer.Add(service_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        service_sizer.Add(self.captcha_service, 1, wx.EXPAND)

        # Ссылка сервиса (только для MultiBot)
        self.url_sizer = wx.BoxSizer(wx.HORIZONTAL)
        url_label = wx.StaticText(panel, label="Ссылка сервиса:")
        self.service_url_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        self.url_sizer.Add(url_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.url_sizer.Add(self.service_url_text, 1, wx.EXPAND)

        # Токен сервиса
        token_sizer = wx.BoxSizer(wx.HORIZONTAL)
        token_label = wx.StaticText(panel, label="Токен сервиса:")
        self.api_key_text = wx.TextCtrl(panel, style=wx.TE_LEFT)
        token_sizer.Add(token_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        token_sizer.Add(self.api_key_text, 1, wx.EXPAND)

        # Таймаут
        timeout_sizer = wx.BoxSizer(wx.HORIZONTAL)
        timeout_label = wx.StaticText(panel, label="Таймаут (сек):")
        self.timeout_spinner = wx.SpinCtrl(panel, min=30, max=300, initial=120)
        timeout_sizer.Add(timeout_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        timeout_sizer.Add(self.timeout_spinner, 0, wx.EXPAND)

        # Задержка
        sleep_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sleep_label = wx.StaticText(panel, label="Задержка (сек):")
        self.sleep_spinner = wx.SpinCtrl(panel, min=1, max=30, initial=5)
        sleep_sizer.Add(sleep_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        sleep_sizer.Add(self.sleep_spinner, 0, wx.EXPAND)

        # SSL проверка
        self.ssl_checkbox = wx.CheckBox(panel, label="Проверять SSL сертификаты")

        sizer.Add(service_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.url_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(token_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(timeout_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(sleep_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.ssl_checkbox, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.AddStretchSpacer(1)

        # Привязка события изменения выбора сервиса
        self.captcha_service.Bind(wx.EVT_CHOICE, self.on_captcha_service_changed)

        panel.SetSizer(sizer)
        return panel

    def _create_browser_tab(self, parent):
        """Создание вкладки браузера"""
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # User Agent
        ua_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ua_label = wx.StaticText(panel, label="User Agent:")
        self.user_agent_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1, 60))
        ua_sizer.Add(ua_label, 0, wx.ALIGN_TOP | wx.RIGHT, 5)
        ua_sizer.Add(self.user_agent_text, 1, wx.EXPAND)

        # Headless режим
        self.headless_checkbox = wx.CheckBox(panel, label="Headless режим (без графического интерфейса)")

        # Разрешение экрана
        resolution_sizer = wx.BoxSizer(wx.HORIZONTAL)
        resolution_label = wx.StaticText(panel, label="Разрешение:")
        width_label = wx.StaticText(panel, label="Ширина:")
        self.width_spinner = wx.SpinCtrl(panel, min=800, max=3840, initial=1920)
        height_label = wx.StaticText(panel, label="Высота:")
        self.height_spinner = wx.SpinCtrl(panel, min=600, max=2160, initial=1080)

        resolution_sizer.Add(resolution_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        resolution_sizer.Add(width_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 2)
        resolution_sizer.Add(self.width_spinner, 0, wx.EXPAND | wx.RIGHT, 10)
        resolution_sizer.Add(height_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 2)
        resolution_sizer.Add(self.height_spinner, 0, wx.EXPAND)

        # Таймауты
        timeouts_sizer = wx.GridSizer(2, 2, 5, 5)

        timeout_label = wx.StaticText(panel, label="Таймаут (мс):")
        self.timeout_spinner_browser = wx.SpinCtrl(panel, min=1000, max=120000, initial=30000)
        nav_timeout_label = wx.StaticText(panel, label="Таймаут навигации (мс):")
        self.nav_timeout_spinner = wx.SpinCtrl(panel, min=1000, max=180000, initial=60000)

        timeouts_sizer.Add(timeout_label, 0, wx.ALIGN_CENTER_VERTICAL)
        timeouts_sizer.Add(self.timeout_spinner_browser, 0, wx.EXPAND)
        timeouts_sizer.Add(nav_timeout_label, 0, wx.ALIGN_CENTER_VERTICAL)
        timeouts_sizer.Add(self.nav_timeout_spinner, 0, wx.EXPAND)

        # Дополнительные опции
        options_sizer = wx.BoxSizer(wx.VERTICAL)
        self.block_resources_checkbox = wx.CheckBox(panel, label="Блокировать ресурсы (изображения, шрифты)")
        self.disable_js_checkbox = wx.CheckBox(panel, label="Отключить JavaScript")
        self.disable_css_checkbox = wx.CheckBox(panel, label="Отключить CSS")

        options_sizer.Add(self.block_resources_checkbox, 0, wx.BOTTOM, 5)
        options_sizer.Add(self.disable_js_checkbox, 0, wx.BOTTOM, 5)
        options_sizer.Add(self.disable_css_checkbox, 0, wx.BOTTOM, 5)

        sizer.Add(ua_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(self.headless_checkbox, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(resolution_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(timeouts_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.Add(options_sizer, 0, wx.EXPAND | wx.BOTTOM, 10)
        sizer.AddStretchSpacer(1)

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

    def _load_current_settings(self):
        """Загрузка текущих настроек"""
        # Авторизация
        self.email_text.SetValue(self.config_data.get('general', {}).get('default_email', ''))
        self.password_text.SetValue(self.config_data.get('general', {}).get('default_password', ''))

        # Капча
        captcha_config = self.config_data.get('captcha', {})
        service_url = captcha_config.get('service_url', 'http://api.multibot.in')

        if 'xevil' in service_url.lower():
            self.captcha_service.SetSelection(1)  # XEvil
            self.service_url_text.Disable()
        else:
            self.captcha_service.SetSelection(0)  # MultiBot
            self.service_url_text.Enable()

        self.service_url_text.SetValue(service_url)
        self.api_key_text.SetValue(captcha_config.get('api_key', ''))
        self.timeout_spinner.SetValue(captcha_config.get('timeout', 120))
        self.sleep_spinner.SetValue(captcha_config.get('sleep', 5))
        self.ssl_checkbox.SetValue(captcha_config.get('verify_ssl', False))

        # Браузер
        browser_config = self.config_data.get('browser', {})
        self.user_agent_text.SetValue(browser_config.get('user_agent', ''))
        self.headless_checkbox.SetValue(browser_config.get('headless', True))
        self.width_spinner.SetValue(browser_config.get('viewport_width', 1920))
        self.height_spinner.SetValue(browser_config.get('viewport_height', 1080))
        self.timeout_spinner_browser.SetValue(browser_config.get('timeout', 30000))
        self.nav_timeout_spinner.SetValue(browser_config.get('navigation_timeout', 60000))
        self.block_resources_checkbox.SetValue(browser_config.get('block_resources', True))
        self.disable_js_checkbox.SetValue(browser_config.get('disable_javascript', False))
        self.disable_css_checkbox.SetValue(browser_config.get('disable_css', False))

    def on_captcha_service_changed(self, event):
        """Обработчик изменения выбора сервиса капчи"""
        selection = self.captcha_service.GetSelection()
        if selection == 0:  # MultiBot
            self.service_url_text.Disable()
            self.service_url_text.SetValue("http://api.multibot.in")
        else:  # XEvil
            self.service_url_text.Enable()
            self.service_url_text.SetValue("")  # XEvil не требует URL

    def on_save(self, event):
        """Сохранение настроек"""
        try:
            # Сохранение авторизации
            if 'general' not in self.config_data:
                self.config_data['general'] = {}
            self.config_data['general']['default_email'] = self.email_text.GetValue()
            self.config_data['general']['default_password'] = self.password_text.GetValue()

            # Сохранение капчи
            if 'captcha' not in self.config_data:
                self.config_data['captcha'] = {}

            captcha_service = self.captcha_service.GetSelection()
            if captcha_service == 0:  # MultiBot
                self.config_data['captcha']['service_url'] = self.service_url_text.GetValue()
            else:  # XEvil
                self.config_data['captcha']['service_url'] = "http://localhost:8000"  # XEvil по умолчанию

            self.config_data['captcha']['api_key'] = self.api_key_text.GetValue()
            self.config_data['captcha']['timeout'] = self.timeout_spinner.GetValue()
            self.config_data['captcha']['sleep'] = self.sleep_spinner.GetValue()
            self.config_data['captcha']['verify_ssl'] = self.ssl_checkbox.GetValue()

            # Сохранение браузера
            if 'browser' not in self.config_data:
                self.config_data['browser'] = {}

            self.config_data['browser']['user_agent'] = self.user_agent_text.GetValue()
            self.config_data['browser']['headless'] = self.headless_checkbox.GetValue()
            self.config_data['browser']['viewport_width'] = self.width_spinner.GetValue()
            self.config_data['browser']['viewport_height'] = self.height_spinner.GetValue()
            self.config_data['browser']['timeout'] = self.timeout_spinner_browser.GetValue()
            self.config_data['browser']['navigation_timeout'] = self.nav_timeout_spinner.GetValue()
            self.config_data['browser']['block_resources'] = self.block_resources_checkbox.GetValue()
            self.config_data['browser']['disable_javascript'] = self.disable_js_checkbox.GetValue()
            self.config_data['browser']['disable_css'] = self.disable_css_checkbox.GetValue()

            # Сохранение в конфигурационный менеджер
            self.config_manager.data = self.config_data
            self.config_manager.save_config()

            wx.MessageBox("Настройки успешно сохранены!", "Успех", wx.OK | wx.ICON_INFORMATION)
            self.EndModal(wx.ID_OK)

        except Exception as e:
            wx.MessageBox(f"Ошибка при сохранении настроек: {e}", "Ошибка", wx.OK | wx.ICON_ERROR)
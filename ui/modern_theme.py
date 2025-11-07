# ui/modern_theme.py
"""
Современная тема для приложения - исправленная версия
"""

import wx
import wx.adv
from typing import Tuple, Dict, Any


class ModernTheme:
    """Современная цветовая схема и стили"""

    # Цветовая палитра
    COLORS = {
        'primary': '#2C3E50',
        'secondary': '#34495E',
        'accent': '#3498DB',
        'success': '#27AE60',
        'warning': '#F39C12',
        'error': '#E74C3C',
        'background': '#ECF0F1',
        'surface': '#FFFFFF',
        'text_primary': '#2C3E50',
        'text_secondary': '#7F8C8D',
    }

    # Стили шрифтов (будут созданы при первом использовании)
    _fonts_initialized = False
    _fonts = {}

    @classmethod
    def _initialize_fonts(cls):
        """Ленивая инициализация шрифтов"""
        if cls._fonts_initialized:
            return

        cls._fonts = {
            'title': wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
            'heading': wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
            'subheading': wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD),
            'normal': wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
            'small': wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL),
        }
        cls._fonts_initialized = True

    @classmethod
    def get_font(cls, font_name: str) -> wx.Font:
        """Получение шрифта по имени"""
        cls._initialize_fonts()
        return cls._fonts.get(font_name, cls._fonts['normal'])

    @classmethod
    def apply_theme(cls, window):
        """Применение темы к окну"""
        if isinstance(window, (wx.Frame, wx.Dialog)):
            window.SetBackgroundColour(cls.COLORS['background'])
        elif isinstance(window, wx.Panel):
            window.SetBackgroundColour(cls.COLORS['surface'])
        elif isinstance(window, wx.ListCtrl):
            window.SetBackgroundColour(cls.COLORS['surface'])
            window.SetForegroundColour(cls.COLORS['text_primary'])

    @classmethod
    def create_modern_button(cls, parent, label: str, color: str = 'accent') -> wx.Button:
        """Создание современной кнопки"""
        btn = wx.Button(parent, label=label)
        btn.SetBackgroundColour(cls.COLORS[color])
        btn.SetForegroundColour(cls.COLORS['surface'])
        btn.SetFont(cls.get_font('normal'))

        # Эффекты при наведении
        def on_enter(e):
            color_obj = wx.Colour(cls.COLORS[color])
            r, g, b = color_obj.Red(), color_obj.Green(), color_obj.Blue()
            hover_color = wx.Colour(max(0, r - 20), max(0, g - 20), max(0, b - 20))
            btn.SetBackgroundColour(hover_color)
            btn.Refresh()

        def on_leave(e):
            btn.SetBackgroundColour(cls.COLORS[color])
            btn.Refresh()

        btn.Bind(wx.EVT_ENTER_WINDOW, on_enter)
        btn.Bind(wx.EVT_LEAVE_WINDOW, on_leave)

        return btn

    @classmethod
    def create_status_label(cls, parent, text: str, status: str = 'normal') -> wx.StaticText:
        """Создание метки статуса"""
        label = wx.StaticText(parent, label=text)

        status_colors = {
            'success': cls.COLORS['success'],
            'warning': cls.COLORS['warning'],
            'error': cls.COLORS['error'],
            'normal': cls.COLORS['text_primary']
        }

        label.SetForegroundColour(status_colors.get(status, cls.COLORS['text_primary']))
        label.SetFont(cls.get_font('small'))

        return label

    @classmethod
    def create_section_title(cls, parent, text: str) -> wx.StaticText:
        """Создание заголовка раздела"""
        title = wx.StaticText(parent, label=text)
        title.SetFont(cls.get_font('heading'))
        title.SetForegroundColour(cls.COLORS['text_primary'])
        return title


class ModernDialog(wx.Dialog):
    """Базовый класс для современных диалогов"""

    def __init__(self, parent, title: str, size: Tuple[int, int] = (500, 400)):
        super().__init__(parent, title=title, size=size,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        ModernTheme.apply_theme(self)

    def add_buttons(self, sizer, on_ok=None, on_cancel=None):
        """Добавление стандартных кнопок"""
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        if on_ok:
            ok_btn = ModernTheme.create_modern_button(self, "OK", 'success')
            ok_btn.Bind(wx.EVT_BUTTON, on_ok)
            button_sizer.Add(ok_btn, 0, wx.RIGHT, 10)

        if on_cancel:
            cancel_btn = ModernTheme.create_modern_button(self, "Отмена", 'error')
            cancel_btn.Bind(wx.EVT_BUTTON, on_cancel)
            button_sizer.Add(cancel_btn, 0)

        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)


class ModernPanel(wx.Panel):
    """Базовый класс для современных панелей"""

    def __init__(self, parent):
        super().__init__(parent)
        ModernTheme.apply_theme(self)
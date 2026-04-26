from __future__ import annotations

import atexit
import ctypes
import ctypes.wintypes
import json
import os
import sys
import threading
import time
import webbrowser
import winreg
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import bm_single_instance

try:
    import winsound
except ImportError:
    winsound = None                                  

try:
    import keyboard
except ImportError:
    keyboard = None                                  

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None                                  
    Image = None                                  

                                                                           
PROJECT_SLUG = "windows-on-top"
SINGLE_APP_ID = "bm-" + PROJECT_SLUG
REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "bm-" + PROJECT_SLUG
APP_VERSION = "V1.0"
WINDOW_TITLE_PREFIX = "[B.M] "
WINDOW_TITLE_SUFFIX = " " + APP_VERSION + " By. [B.M] 圓周率 3.14"
ABOUT_URL = "http://exnormal.com:81/"
WINDOW_POS_X = 100
WINDOW_POS_Y = 100
WIN_W, WIN_H = 370, 170
DEFAULT_TK_FONT_SIZE = 10

SWP_NOOWNERZORDER = 0x0200
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x0008
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
GA_ROOT = 2
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
INVALID_HANDLE = ctypes.c_void_p(-1).value                            


def _apply_default_font_size(root: tk.Tk) -> None:
    for name in (
        "TkDefaultFont",
        "TkTextFont",
        "TkFixedFont",
        "TkMenuFont",
        "TkHeadingFont",
        "TkCaptionFont",
        "TkSmallCaptionFont",
        "TkIconFont",
        "TkTooltipFont",
    ):
        try:
            tkfont.nametofont(name).configure(size=DEFAULT_TK_FONT_SIZE)
        except tk.TclError:
            pass

HOTKEY_KEY_TO_KEYBOARD = {
    ",": ",",
    ".": ".",
    "/": "/",
    "-": "-",
    "=": "=",
    "+": "plus",
    "INSERT": "insert",
    "DELETE": "delete",
    "HOME": "home",
    "END": "end",
    "PAGEUP": "page up",
    "PAGEDOWN": "page down",
    "UP": "up",
    "DOWN": "down",
    "LEFT": "left",
    "RIGHT": "right",
    "PRINTSCREEN": "print screen",
    "PAUSE": "pause",
    "SCROLLLOCK": "scroll lock",
    "NUMPAD0": "num 0",
    "NUMPAD1": "num 1",
    "NUMPAD2": "num 2",
    "NUMPAD3": "num 3",
    "NUMPAD4": "num 4",
    "NUMPAD5": "num 5",
    "NUMPAD6": "num 6",
    "NUMPAD7": "num 7",
    "NUMPAD8": "num 8",
    "NUMPAD9": "num 9",
    "NUMPADADD": "add",
    "NUMPADSUB": "subtract",
    "NUMPADDIV": "divide",
    "NUMPADMUL": "multiply",
}


def _hwnd_insert_after(v: int):
    return ctypes.wintypes.HWND(int(v))


def _set_app_user_model_id(title: str) -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(str(title))
    except Exception:
        pass


def _primary_screen_origin() -> Tuple[int, int]:
    if sys.platform != "win32":
        return 0, 0
    try:
        MONITOR_DEFAULTTOPRIMARY = 1

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        u = ctypes.windll.user32
        m = u.MonitorFromPoint(POINT(0, 0), MONITOR_DEFAULTTOPRIMARY)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if m and u.GetMonitorInfoW(m, ctypes.byref(mi)):
            return int(mi.rcMonitor.left), int(mi.rcMonitor.top)
    except Exception:
        pass
    return 0, 0


if ctypes.sizeof(ctypes.c_void_p) == 8:
    _GWL = user32.GetWindowLongPtrW
    _SWL = user32.SetWindowLongPtrW
else:
    _GWL = user32.GetWindowLongW
    _SWL = user32.SetWindowLongW

try:
    user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.wintypes.UINT,
    ]
    user32.SetWindowPos.restype = ctypes.wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    user32.GetAncestor.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT]
    user32.GetAncestor.restype = ctypes.wintypes.HWND
    _GWL.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
    _GWL.restype = (
        ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    )
except Exception:
    pass


def _base_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(sys._MEIPASS)                              
    return os.path.dirname(os.path.abspath(__file__))


def _data_path(*parts: str) -> str:
    return os.path.join(_base_dir(), *parts)


def play_switch_sound() -> bool:
    if winsound is None:
        return False
    try:
        p = _data_path("wav", "switch.wav")
        p = os.path.normpath(p)
        if os.path.isfile(p):
            winsound.PlaySound(
                p,
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return True
        winsound.MessageBeep(-1)
        return True
    except Exception:
        try:
            winsound.Beep(880, 80)
            return True
        except Exception:
            return False


def _config_basename() -> str:
    return f"bm-{PROJECT_SLUG}.json"


def _config_dir() -> str:
    if getattr(sys, "frozen", False) and sys.executable:
        return os.path.normpath(os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.normpath(os.path.dirname(os.path.abspath(__file__)))


def _config_path() -> str:
    return os.path.join(_config_dir(), _config_basename())


BUILTIN_I18N_ORDER = ("zh_TW", "zh_CN", "ja_JP", "en_US")


def _reference_i18n_keys() -> frozenset:
    return frozenset(_default_config_dict()["languages"]["zh_TW"].keys())


def _default_config_dict() -> Dict[str, Any]:
    return {
        "settings": {
            "languages": "zh_TW",
            "auto_start": False,
            "auto_minimize": False,
            "hotkey": {
                "ctrl": True,
                "win": False,
                "alt": False,
                "key": "F8",
            },
        },
        "languages": {
            "zh_TW": {
                "language_name": "繁體中文",
                "settings": "設定",
                "project_name": "視窗置頂",
                "hotkey_label": "快捷鍵：",
                "autostart_checkbox": "跟著 Windows 啟動",
                "auto_minimize_checkbox": "啟動後自動縮小",
                "btn_hotkey_save": "儲存",
                "btn_hotkey_restore": "還原預設",
                "about": "關於",
                "exit": "離開",
                "help_text": "本軟體啟動時，對著要置頂的視窗按下快捷鍵即可。",
            },
            "zh_CN": {
                "language_name": "简体中文",
                "settings": "设置",
                "project_name": "窗口置顶",
                "hotkey_label": "快捷键：",
                "autostart_checkbox": "随 Windows 启动",
                "auto_minimize_checkbox": "启动后自动最小化",
                "btn_hotkey_save": "保存",
                "btn_hotkey_restore": "恢复默认",
                "about": "关于",
                "exit": "离开",
                "help_text": "启动本软件后，对需要置顶的窗口按下快捷键即可。",
            },
            "ja_JP": {
                "language_name": "日本語",
                "settings": "設定",
                "project_name": "最前面表示",
                "hotkey_label": "ショートカット：",
                "autostart_checkbox": "Windows 起動時に実行",
                "auto_minimize_checkbox": "起動後に最小化",
                "btn_hotkey_save": "保存",
                "btn_hotkey_restore": "既定に戻す",
                "about": "バージョン情報",
                "exit": "終了",
                "help_text": "本ソフト起動中、最前面にしたいウィンドウにショートカットキーを押してください。",
            },
            "en_US": {
                "language_name": "English",
                "settings": "Settings",
                "project_name": "Window On Top",
                "hotkey_label": "Hotkey:",
                "autostart_checkbox": "Start with Windows",
                "auto_minimize_checkbox": "Start minimized",
                "btn_hotkey_save": "Save",
                "btn_hotkey_restore": "Restore default",
                "about": "About",
                "exit": "Exit",
                "help_text": "After launching, focus the target window and press the hotkey to toggle always on top.",
            },
        },
    }


def _is_valid_config(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    st = d.get("settings")
    if not isinstance(st, dict):
        return False
    code = st.get("languages")
    if not isinstance(code, str) or not str(code).strip():
        return False
    code = str(code).strip()
    lg = d.get("languages")
    if not isinstance(lg, dict) or not lg or code not in lg:
        return False
    ref_keys = _reference_i18n_keys()
    for _k, m in lg.items():
        if not isinstance(m, dict):
            return False
        if frozenset(m.keys()) != ref_keys:
            return False
        for rk in ref_keys:
            v = m.get(rk)
            if not isinstance(v, str):
                return False
            if rk in ("language_name", "project_name", "settings") and not v.strip():
                return False
    hk = st.get("hotkey")
    if not isinstance(hk, dict):
        return False
    for req in ("ctrl", "alt", "win", "key"):
        if req not in hk:
            return False
    for k0 in ("auto_start", "auto_minimize"):
        if not isinstance(st.get(k0), bool):
            return False
    return True


def _merge_lang_defaults(d: Dict[str, Any]) -> None:
    try:
        base = _default_config_dict().get("languages") or {}
        lg = d.get("languages")
        if not isinstance(lg, dict):
            return
        for code, d_lang in base.items():
            if code not in lg or not isinstance(lg[code], dict):
                continue
            cur = lg[code]
            for k, v in d_lang.items():
                if k not in cur:
                    cur[k] = v
    except Exception:
        pass


def _load_config() -> Dict[str, Any]:
    path = _config_path()
    if not os.path.isfile(path):
        d = _default_config_dict()
        _save_config_atomic(d, path)
        return d
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
        d = json.loads(raw)
        if not _is_valid_config(d):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except Exception:
                pass
            d = _default_config_dict()
            _save_config_atomic(d, path)
            return d
        _merge_lang_defaults(d)
        return d
    except Exception:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        d = _default_config_dict()
        _save_config_atomic(d, path)
        return d


def _save_config_atomic(data: Dict[str, Any], path: Optional[str] = None) -> None:
    p = path or _config_path()
    tmp = p + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except Exception:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            pass


_HOTKEY_SPECIAL_VK: Dict[str, int] = {
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    "-": 0xBD,
    "=": 0xBB,
    "+": 0xBB,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "HOME": 0x24,
    "END": 0x23,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "UP": 0x26,
    "DOWN": 0x28,
    "LEFT": 0x25,
    "RIGHT": 0x27,
    "PRINTSCREEN": 0x2C,
    "PAUSE": 0x13,
    "SCROLLLOCK": 0x91,
    "NUMPAD0": 0x60,
    "NUMPAD1": 0x61,
    "NUMPAD2": 0x62,
    "NUMPAD3": 0x63,
    "NUMPAD4": 0x64,
    "NUMPAD5": 0x65,
    "NUMPAD6": 0x66,
    "NUMPAD7": 0x67,
    "NUMPAD8": 0x68,
    "NUMPAD9": 0x69,
    "NUMPADADD": 0x6B,
    "NUMPADSUB": 0x6D,
    "NUMPADDIV": 0x6F,
    "NUMPADMUL": 0x6A,
}


def _normalize_hotkey_token(text: str) -> Optional[str]:
    t = (text or "").strip().upper()
    if not t:
        return None
    if t.startswith("F") and len(t) >= 2 and t[1:].isdigit():
        try:
            n = int(t[1:])
            if 1 <= n <= 12:
                return "F" + str(n)
        except ValueError:
            return None
    if len(t) == 1 and t.isascii() and t.isalnum():
        return t
    if t in _HOTKEY_SPECIAL_VK:
        return t
    aliases = {
        "PAGE UP": "PAGEUP",
        "PAGE DOWN": "PAGEDOWN",
        "PGUP": "PAGEUP",
        "PGDN": "PAGEDOWN",
        "PRTSC": "PRINTSCREEN",
        "PRINT": "PRINTSCREEN",
        "SCROLL LOCK": "SCROLLLOCK",
        "NUMPAD+": "NUMPADADD",
        "NUMPAD-": "NUMPADSUB",
        "NUMPAD/": "NUMPADDIV",
        "NUMPAD*": "NUMPADMUL",
        "KP_ADD": "NUMPADADD",
        "KP_SUBTRACT": "NUMPADSUB",
        "KP_DIVIDE": "NUMPADDIV",
        "KP_MULTIPLY": "NUMPADMUL",
    }
    if t in aliases:
        return aliases[t]
    return None


def _serialize_hotkey_key(text: str) -> str:
    return _normalize_hotkey_token(text) or "F8"


def _get_foreground_hwnd() -> int:
    return int(user32.GetForegroundWindow() or 0)


def _get_root_hwnd(hwnd: int) -> int:
    if not hwnd:
        return 0
    r = int(user32.GetAncestor(int(hwnd), GA_ROOT) or 0)
    return r or int(hwnd)


def _get_top_level_for_topmost(h: int) -> int:
    return int(_get_root_hwnd(int(h or 0)) or 0)


def _is_hwnd_topmost(hwnd: int) -> bool:
    if not hwnd:
        return False
    ex = int(_GWL(int(hwnd), GWL_EXSTYLE) or 0)
    return bool(ex & WS_EX_TOPMOST)


def _toggle_topmost_for_hwnd(hwnd: int) -> Optional[bool]:
    if not hwnd:
        return None
    try:
        was_top = _is_hwnd_topmost(int(hwnd))
        if was_top:
            after = HWND_NOTOPMOST
            f = int(SWP_NOMOVE) | int(SWP_NOSIZE) | SWP_NOOWNERZORDER
        else:
            after = HWND_TOPMOST
            f = (
                int(SWP_NOMOVE)
                | int(SWP_NOSIZE)
                | SWP_NOOWNERZORDER
                | int(SWP_SHOWWINDOW)
            )
        if not user32.SetWindowPos(
            int(hwnd), _hwnd_insert_after(int(after)), 0, 0, 0, 0, f
        ):
            return None
        return _is_hwnd_topmost(int(hwnd))
    except Exception:
        return None


def _get_exe_path_for_autostart() -> str:
    if getattr(sys, "frozen", False) and sys.executable:
        return os.path.normpath(sys.executable)
    return os.path.normpath(os.path.abspath(sys.argv[0]))


def _set_auto_start(en: bool) -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
    except Exception:
        return
    try:
        if en:
            winreg.SetValueEx(
                key, REG_VALUE_NAME, 0, winreg.REG_SZ, _get_exe_path_for_autostart()
            )
        else:
            try:
                winreg.DeleteValue(key, REG_VALUE_NAME)
            except OSError:
                pass
    except Exception:
        pass
    try:
        winreg.CloseKey(key)
    except Exception:
        pass


class WindowsOnTopApp:
    def __init__(self, mutex_handle: int) -> None:
        self._mutex_handle = mutex_handle
        self._data = _load_config()
        self._topmost_hwnds: Set[int] = set()
        self._hotkey_registered = False
        self._pipe_quit_done = False

        self.root = tk.Tk()
        _apply_default_font_size(self.root)
        self.root.title(self._window_title_full())
        self._set_app_user_model_id()
        ox, oy = _primary_screen_origin()
        self.root.geometry(
            f"{WIN_W}x{WIN_H}+{ox + WINDOW_POS_X}+{oy + WINDOW_POS_Y}"
        )
        self.root.resizable(False, False)

        st = self._data.get("settings") or {}
        hk = st.get("hotkey") or {}
        self._var_ctrl = tk.BooleanVar(value=bool(hk.get("ctrl", True)))
        self._var_win = tk.BooleanVar(value=bool(hk.get("win")))
        self._var_alt = tk.BooleanVar(value=bool(hk.get("alt")))
        self._var_key = tk.StringVar(
            value=_serialize_hotkey_key(str(hk.get("key") or "F8"))
        )
        self._var_autostart = tk.BooleanVar(value=bool(st.get("auto_start")))
        self._var_minimize = tk.BooleanVar(value=bool(st.get("auto_minimize")))

        self._tray_icon: Any = None
        self._build_ui()
        self._install_ttk_focus_ring_mitigation()
        self._apply_window_icon()
        self._bind_unmap()
        self.root.bind("<Activate>", self._on_root_activate, add="+")
        self.root.bind("<Deactivate>", self._on_root_deactivate, add="+")
        self.root.bind("<FocusIn>", self._on_root_focus_in, add="+")
        self._bind_space_guards()
        atexit.register(self._cleanup_hotkeys_silent)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_clicked)
        self.root.after(80, self._register_global_hotkey)
        self._start_tray()
        _set_auto_start(self._var_autostart.get())

    def _set_app_user_model_id(self) -> None:
        _set_app_user_model_id(self._window_title_full())

    def _window_title_full(self) -> str:
        code = self._current_lang()
        L = (self._data.get("languages") or {}).get(code) or {}
        p = (L.get("project_name") or PROJECT_SLUG).strip()
        return WINDOW_TITLE_PREFIX + p + WINDOW_TITLE_SUFFIX

    def _lang_codes_ordered(self) -> List[str]:
        langs = self._data.get("languages") or {}
        if not isinstance(langs, dict):
            return list(BUILTIN_I18N_ORDER)
        out = [c for c in BUILTIN_I18N_ORDER if c in langs]
        for k in langs.keys():
            if k not in out:
                out.append(k)
        return out

    def _current_lang(self) -> str:
        s = (self._data.get("settings") or {}).get("languages")
        codes = self._lang_codes_ordered()
        if isinstance(s, str) and s in codes:
            return s
        return codes[0] if codes else "zh_TW"

    def _apply_window_icon(self) -> None:
        ico = os.path.abspath(os.path.normpath(_data_path("icons", "icon.ico")))
        if not os.path.isfile(ico):
            return
        try:
            self.root.iconbitmap(default=ico)
        except tk.TclError:
            try:
                self.root.iconbitmap(ico)
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        row0 = ttk.Frame(main)
        row0.pack(fill=tk.X, pady=(0, 10))
        row0.columnconfigure(0, weight=1)
        row0.columnconfigure(1, weight=1)
        self._chk_autostart = ttk.Checkbutton(
            row0,
            variable=self._var_autostart,
            command=self._on_autostart_toggled,
        )
        self._chk_autostart.configure(takefocus=False)
        self._chk_autostart.grid(row=0, column=0, sticky=tk.W)
        self._chk_min = ttk.Checkbutton(
            row0, variable=self._var_minimize, command=self._on_minimize_toggled
        )
        self._chk_min.configure(takefocus=False)
        self._chk_min.grid(row=0, column=1, sticky=tk.E)

        row1 = ttk.Frame(main)
        row1.pack(fill=tk.X, pady=4)
        self._lbl_hotkey = ttk.Label(row1)
        self._lbl_hotkey.configure(takefocus=False)
        self._lbl_hotkey.pack(side=tk.LEFT, padx=(0, 6))
        self._hk_ctrl = ttk.Checkbutton(
            row1, text="Ctrl", variable=self._var_ctrl, command=self._on_hotkey_mods
        )
        self._hk_ctrl.configure(takefocus=False)
        self._hk_ctrl.pack(side=tk.LEFT)
        self._hk_alt = ttk.Checkbutton(
            row1, text="Alt", variable=self._var_alt, command=self._on_hotkey_mods
        )
        self._hk_alt.configure(takefocus=False)
        self._hk_alt.pack(side=tk.LEFT, padx=(6, 0))
        self._hk_win = ttk.Checkbutton(
            row1, text="Win", variable=self._var_win, command=self._on_hotkey_mods
        )
        self._hk_win.configure(takefocus=False)
        self._hk_win.pack(side=tk.LEFT, padx=(6, 6))
        self._ent_key = ttk.Entry(
            row1,
            textvariable=self._var_key,
            width=8,
            justify="center",
            state="readonly",
        )
        self._ent_key.configure(takefocus=False)
        self._ent_key.pack(side=tk.LEFT)
        self._ent_key.bind("<KeyPress>", self._on_hotkey_entry_keypress, add="+")
        self._ent_key.bind("<KeyRelease>", self._on_hotkey_entry_keyrelease, add="+")
        self._ent_key.bind("<FocusIn>", self._on_hotkey_entry_focus_in, add="+")
        self._ent_key.bind("<FocusOut>", self._on_hotkey_entry_focus_out, add="+")
        self._ent_key.bind("<Button-1>", self._on_hotkey_entry_mouse_press, add="+")
        self._ent_key.bind("<Double-Button-1>", self._on_hotkey_entry_mouse_press, add="+")
        self._ent_key.bind("<Triple-Button-1>", self._on_hotkey_entry_mouse_press, add="+")
        self._ent_key.bind("<B1-Motion>", self._on_hotkey_entry_drag, add="+")

        row2 = ttk.Frame(main)
        row2.pack(fill=tk.X, pady=(6, 0))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)
        row2.columnconfigure(2, weight=1)
        self._btn_hk_save = ttk.Button(
            row2, command=self._on_hotkey_save, takefocus=False
        )
        self._btn_hk_save.grid(row=0, column=0, sticky=tk.W)
        self._btn_hk_restore = ttk.Button(
            row2, command=self._on_hotkey_restore, takefocus=False
        )
        self._btn_hk_restore.grid(row=0, column=1)
        self._btn_lang = ttk.Button(
            row2, command=self._on_cycle_language, takefocus=False
        )
        self._btn_lang.grid(row=0, column=2, sticky=tk.E)

        self._help = ttk.Label(main, wraplength=WIN_W - 40, justify=tk.LEFT)
        self._help.configure(takefocus=False)
        self._help.pack(fill=tk.X, anchor=tk.W, pady=(8, 0))

        self._apply_all_ui_texts()

    def _defocus_toplevel_of(self, w: tk.Widget) -> None:
        try:
            t = w.winfo_toplevel()
            if t and t.winfo_exists():
                t.focus_set()
        except Exception:
            pass

    def _on_ttk_buttonlike_release(self, event: tk.Event) -> None:
        self.root.after_idle(lambda: self._defocus_toplevel_of(event.widget))

    def _install_ttk_focus_ring_mitigation(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.configure("TButton", focuscolor=style.lookup("TButton", "background"))
        except tk.TclError:
            pass
        try:
            bg = style.lookup("TCheckbutton", "background")
            style.configure("TCheckbutton", focuscolor=bg)
            style.map("TCheckbutton", focuscolor=[("focus", bg), ("!focus", bg)])
        except tk.TclError:
            pass
        if getattr(self, "_ttk_focus_release_bind_done", False):
            return
        self._ttk_focus_release_bind_done = True
        self.root.bind_class("TButton", "<ButtonRelease-1>", self._on_ttk_buttonlike_release, add="+")
        self.root.bind_class("TCheckbutton", "<ButtonRelease-1>", self._on_ttk_buttonlike_release, add="+")

    def _space_widgets(self) -> List[tk.Widget]:
        return [
            self._btn_lang,
            self._chk_autostart,
            self._chk_min,
            self._lbl_hotkey,
            self._hk_ctrl,
            self._hk_alt,
            self._hk_win,
            self._ent_key,
            self._btn_hk_save,
            self._btn_hk_restore,
        ]

    def _bind_space_guards(self) -> None:
        self.root.bind_all("<KeyPress-space>", self._on_space_guard, add="+")
        self.root.bind_all("<KeyRelease-space>", self._on_space_guard, add="+")
        for w in self._space_widgets():
            w.bind("<KeyPress-space>", lambda _e: "break", add="+")
            w.bind("<KeyRelease-space>", lambda _e: "break", add="+")

    def _on_space_guard(self, event: tk.Event) -> Optional[str]:
        w = self.root.focus_get() or event.widget
        if w in self._space_widgets():
            return "break"
        cls = str(getattr(w, "winfo_class", lambda: "")())
        if cls in ("TButton", "Button", "TCheckbutton", "Checkbutton"):
            return "break"
        return None

    def _bind_unmap(self) -> None:
        self.root.bind("<Unmap>", self._on_root_unmap, add="+")

    def _on_root_unmap(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        if self.root.state() == "iconic":
            self.root.after(10, self._hide_to_tray)

    def _hide_to_tray(self) -> None:
        try:
            self.root.withdraw()
        except tk.TclError:
            pass

    def _leave_hotkey_entry_focus(self) -> None:
        try:
            if self.root.focus_get() == self._ent_key:
                self.root.focus_set()
        except Exception:
            pass

    def _on_root_activate(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return

        def _defer() -> None:
            self._leave_hotkey_entry_focus()

        try:
            self.root.after_idle(_defer)
        except Exception:
            _defer()

    def _on_root_deactivate(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return
        self._leave_hotkey_entry_focus()

    def _on_root_focus_in(self, event: tk.Event) -> None:
        if event.widget is not self.root:
            return

        def _defer() -> None:
            self._leave_hotkey_entry_focus()

        try:
            self.root.after_idle(_defer)
        except Exception:
            _defer()

    def _apply_all_ui_texts(self) -> None:
        self.root.title(self._window_title_full())
        self._set_app_user_model_id()
        code = self._current_lang()
        L = (self._data.get("languages") or {}).get(code) or {}
        self._btn_lang.configure(
            text=(L.get("language_name") or "…").strip() or "…",
            width=max(10, len((L.get("language_name") or "…")) // 2 + 2),
        )
        self._lbl_hotkey.configure(
            text=(L.get("hotkey_label") or "快捷鍵：").strip() or "快捷鍵："
        )
        self._chk_autostart.configure(
            text=(L.get("autostart_checkbox") or "").strip() or "…"
        )
        self._chk_min.configure(
            text=(L.get("auto_minimize_checkbox") or "").strip() or "…"
        )
        self._btn_hk_save.configure(text=(L.get("btn_hotkey_save") or "儲存").strip())
        self._btn_hk_restore.configure(
            text=(L.get("btn_hotkey_restore") or "還原預設").strip()
        )
        self._help.configure(
            text=(
                L.get("help_text")
                or "本軟體啟動時，對著要置頂的視窗按下快捷鍵即可。"
            )
        )
        if self._tray_icon is not None and pystray is not None:
            try:
                self._tray_icon.menu = self._tray_build_menu()
                if hasattr(self._tray_icon, "update_menu"):
                    self._tray_icon.update_menu()
                self._tray_icon.title = self._tray_tooltip_text()
            except Exception:
                pass

    def _tray_tooltip_text(self) -> str:
        code = self._current_lang()
        L = (self._data.get("languages") or {}).get(code) or {}
        p = (L.get("project_name") or PROJECT_SLUG).strip() or PROJECT_SLUG
        return WINDOW_TITLE_PREFIX + p + WINDOW_TITLE_SUFFIX

    def _tray_build_menu(self) -> Any:
        if pystray is None:
            raise RuntimeError("pystray required")
        L = (self._data.get("languages") or {}).get(self._current_lang()) or {}
        t_about = (L.get("about") or "關於").strip() or "關於"
        t_quit = (L.get("exit") or "離開").strip() or "離開"
        return pystray.Menu(
            pystray.MenuItem(
                " ",
                lambda _i, _it: self.root.after(0, self._restore_from_tray),
                default=True,
                visible=False,
            ),
            pystray.MenuItem(t_about, lambda _i, _it: self.root.after(0, self._open_about)),
            pystray.MenuItem(t_quit, lambda _i, _it: self.root.after(0, self._on_close_clicked)),
        )

    def _start_tray(self) -> None:
        if pystray is None or Image is None:
            return
        try:
            ip = _data_path("icons", "icon.png")
            if os.path.isfile(ip):
                img = Image.open(ip).convert("RGBA")
            else:
                img = Image.open(_data_path("icons", "icon.ico")).convert("RGBA")
        except Exception:
            return
        try:
            self._tray_icon = pystray.Icon(
                "bm_wot",
                img,
                self._tray_tooltip_text(),
                self._tray_build_menu(),
            )
            self._tray_icon.run_detached()
        except Exception:
            self._tray_icon = None

    def _restore_from_tray(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        ox, oy = _primary_screen_origin()
        self.root.geometry(f"+{ox + WINDOW_POS_X}+{oy + WINDOW_POS_Y}")
        self.root.lift()
        try:
            self.root.focus_force()
        except tk.TclError:
            pass
        wh = int(self.root.winfo_id() or 0)
        if wh:
            try:
                user32.BringWindowToTop(wh)
            except Exception:
                pass

    def _open_about(self) -> None:
        try:
            webbrowser.open(ABOUT_URL)
        except Exception:
            pass

    def _persist_hotkey_to_data(self) -> None:
        st = self._data.get("settings")
        if not isinstance(st, dict):
            st = {}
            self._data["settings"] = st
        ctrl = bool(self._var_ctrl.get())
        win_ = bool(self._var_win.get())
        alt = bool(self._var_alt.get())
        if not (ctrl or win_ or alt):
            ctrl = True
            self._var_ctrl.set(True)
        st["hotkey"] = {
            "ctrl": ctrl,
            "win": win_,
            "alt": alt,
            "key": _serialize_hotkey_key(self._var_key.get()),
        }

    def _on_autostart_toggled(self) -> None:
        st = self._data.get("settings")
        if not isinstance(st, dict):
            st = {}
            self._data["settings"] = st
        st["auto_start"] = bool(self._var_autostart.get())
        _set_auto_start(st["auto_start"])
        try:
            _save_config_atomic(self._data)
        except Exception:
            pass
        self._apply_all_ui_texts()

    def _on_minimize_toggled(self) -> None:
        st = self._data.get("settings")
        if not isinstance(st, dict):
            st = {}
            self._data["settings"] = st
        st["auto_minimize"] = bool(self._var_minimize.get())
        try:
            _save_config_atomic(self._data)
        except Exception:
            pass
        self._apply_all_ui_texts()

    def _on_cycle_language(self) -> None:
        self._leave_hotkey_entry_focus()
        codes = self._lang_codes_ordered()
        if not codes:
            return
        cur = self._current_lang()
        i = (codes.index(cur) + 1) % len(codes) if cur in codes else 0
        st = self._data.get("settings")
        if not isinstance(st, dict):
            st = {}
            self._data["settings"] = st
        st["languages"] = codes[i]
        try:
            _save_config_atomic(self._data)
        except Exception:
            pass
        self._apply_all_ui_texts()

    def _on_hotkey_mods(self) -> None:
        self._persist_hotkey_to_data()
        try:
            _save_config_atomic(self._data)
        except Exception:
            pass
        self._register_global_hotkey()

    def _on_hotkey_save(self) -> None:
        self._leave_hotkey_entry_focus()
        self._persist_hotkey_to_data()
        try:
            _save_config_atomic(self._data)
        except Exception:
            pass
        self._register_global_hotkey()
        play_switch_sound()

    def _on_hotkey_restore(self) -> None:
        self._leave_hotkey_entry_focus()
        d = dict(_default_config_dict()["settings"]["hotkey"])
        self._var_ctrl.set(bool(d.get("ctrl")))
        self._var_win.set(bool(d.get("win")))
        self._var_alt.set(bool(d.get("alt")))
        self._var_key.set(_serialize_hotkey_key(str(d.get("key") or "F8")))
        self._on_hotkey_save()

    def _normalize_key_var(self) -> str:
        return _serialize_hotkey_key(self._var_key.get())

    def _end_hotkey_key_listen(self) -> None:
        try:
            self.root.focus_set()
        except tk.TclError:
            pass

    def _on_hotkey_entry_keypress(self, event: tk.Event) -> Optional[str]:
        ks = (event.keysym or "").upper()
        if ks in ("BACKSPACE", "DELETE"):
            self._var_key.set("")
            return "break"
        if ks == "ESCAPE":
            self._end_hotkey_key_listen()
            return "break"
        if ks == "SPACE":
            return "break"
        if ks.startswith("F") and ks[1:].isdigit():
            n = int(ks[1:])
            if 1 <= n <= 12:
                self._var_key.set(f"F{n}")
                self._end_hotkey_key_listen()
                return "break"
        if len(ks) == 1 and ks.isascii() and ks.isalnum():
            self._var_key.set(ks)
            self._end_hotkey_key_listen()
            return "break"
        symbol_map = {
            "COMMA": ",",
            "PERIOD": ".",
            "SLASH": "/",
            "MINUS": "-",
            "EQUAL": "=",
            "PLUS": "+",
        }
        if ks in symbol_map:
            self._var_key.set(symbol_map[ks])
            self._end_hotkey_key_listen()
            return "break"
        nav_map = {
            "INSERT": "INSERT",
            "DELETE": "DELETE",
            "HOME": "HOME",
            "END": "END",
            "PRIOR": "PAGEUP",
            "NEXT": "PAGEDOWN",
            "PAGE_UP": "PAGEUP",
            "PAGE_DOWN": "PAGEDOWN",
            "UP": "UP",
            "DOWN": "DOWN",
            "LEFT": "LEFT",
            "RIGHT": "RIGHT",
            "PRINT": "PRINTSCREEN",
            "SNAPSHOT": "PRINTSCREEN",
            "PAUSE": "PAUSE",
            "SCROLL_LOCK": "SCROLLLOCK",
        }
        if ks in nav_map:
            self._var_key.set(nav_map[ks])
            self._end_hotkey_key_listen()
            return "break"
        if ks.startswith("KP_"):
            kp_map = {
                "KP_0": "NUMPAD0",
                "KP_1": "NUMPAD1",
                "KP_2": "NUMPAD2",
                "KP_3": "NUMPAD3",
                "KP_4": "NUMPAD4",
                "KP_5": "NUMPAD5",
                "KP_6": "NUMPAD6",
                "KP_7": "NUMPAD7",
                "KP_8": "NUMPAD8",
                "KP_9": "NUMPAD9",
                "KP_ADD": "NUMPADADD",
                "KP_SUBTRACT": "NUMPADSUB",
                "KP_DIVIDE": "NUMPADDIV",
                "KP_MULTIPLY": "NUMPADMUL",
            }
            m = kp_map.get(ks)
            if m:
                self._var_key.set(m)
                self._end_hotkey_key_listen()
                return "break"
        return "break"

    def _on_hotkey_entry_mouse_press(self, _event: tk.Event) -> str:
        self._ent_key.focus_set()
        try:
            self._ent_key.selection_clear()
        except tk.TclError:
            pass
        self._ent_key.icursor(tk.END)
        return "break"

    def _on_hotkey_entry_keyrelease(self, _event: tk.Event) -> None:
        self._var_key.set(_serialize_hotkey_key(self._var_key.get()))

    def _on_hotkey_entry_drag(self, _event: tk.Event) -> str:
        try:
            self._ent_key.selection_clear()
        except tk.TclError:
            pass
        return "break"

    def _on_hotkey_entry_focus_in(self, _event: tk.Event) -> None:
        self._unregister_global_hotkey()

    def _on_hotkey_entry_focus_out(self, _event: tk.Event) -> None:
        self._var_key.set(self._normalize_key_var())
        self.root.after(0, self._register_global_hotkey)

    def _build_keyboard_combo(self) -> Optional[str]:
        if keyboard is None:
            return None
        self._persist_hotkey_to_data()
        hk = (self._data.get("settings") or {}).get("hotkey") or {}
        key = _serialize_hotkey_key(str(hk.get("key") or "F8"))
        parts: List[str] = []
        if hk.get("ctrl"):
            parts.append("ctrl")
        if hk.get("alt"):
            parts.append("alt")
        if hk.get("win"):
            parts.append("windows")
        if key.startswith("F") and key[1:].isdigit():
            parts.append("f" + key[1:])
        else:
            parts.append(HOTKEY_KEY_TO_KEYBOARD.get(key, key.lower()))
        return "+".join(parts)

    def _unregister_global_hotkey(self) -> None:
        try:
            if keyboard is not None:
                keyboard.clear_all_hotkeys()
        except Exception:
            pass
        self._hotkey_registered = False

    def _register_global_hotkey(self) -> None:
        self._unregister_global_hotkey()
        if keyboard is None:
            return
        try:
            if self.root.focus_get() == self._ent_key:
                return
        except Exception:
            pass
        combo = self._build_keyboard_combo()
        if not combo:
            return
        try:
            keyboard.add_hotkey(combo, self._on_hotkey_keyboard, suppress=False)
            self._hotkey_registered = True
        except Exception:
            self._hotkey_registered = False

    def _cleanup_hotkeys_silent(self) -> None:
        try:
            if keyboard is not None:
                keyboard.clear_all_hotkeys()
        except Exception:
            pass

    def _on_hotkey_keyboard(self) -> None:
        fg = int(_get_foreground_hwnd() or 0)

        def _go() -> None:
            self._do_hotkey_action(fg)

        try:
            self.root.after(0, _go)
        except Exception:
            pass

    def _pick_target_for_hotkey(self, fg_at_hot: int) -> int:
        self_hwnd = int(self.root.winfo_id() or 0)
        candidates = [int(_get_foreground_hwnd() or 0), int(fg_at_hot or 0)]
        for h in candidates:
            if not h:
                continue
            r = int(_get_top_level_for_topmost(h) or 0)
            if not r or (self_hwnd and r == self_hwnd):
                continue
            return int(r)
        return 0

    def _do_hotkey_action(self, fg_at_hot: int = 0) -> None:
        try:
            play_switch_sound()
            r = self._pick_target_for_hotkey(int(fg_at_hot or 0))
            if not r:
                return
            now_top = _toggle_topmost_for_hwnd(r)
            if now_top is None:
                return
            if now_top:
                self._topmost_hwnds.add(r)
            else:
                self._topmost_hwnds.discard(r)
        except Exception:
            pass

    def _clear_all_topmost(self) -> None:
        for h in list(self._topmost_hwnds):
            try:
                f = int(SWP_NOMOVE) | int(SWP_NOSIZE) | SWP_NOOWNERZORDER
                user32.SetWindowPos(
                    int(h),
                    _hwnd_insert_after(int(HWND_NOTOPMOST)),
                    0,
                    0,
                    0,
                    0,
                    f,
                )
            except Exception:
                pass
        self._topmost_hwnds.clear()

    def schedule_quit_from_pipe(self) -> None:
        if self._pipe_quit_done:
            return
        self._pipe_quit_done = True
        self.root.after(0, self._on_close_clicked)

    def _on_close_clicked(self) -> None:
        self._clear_all_topmost()
        self._unregister_global_hotkey()
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        if self._mutex_handle:
            bm_single_instance.release_mutex(self._mutex_handle)
            self._mutex_handle = 0
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def maybe_start_minimized(self) -> None:
        st = (self._data.get("settings") or {})
        if bool(st.get("auto_minimize")):
            self.root.after(0, lambda: self.root.iconify())

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
                                                                          
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    mh = bm_single_instance.acquire_or_handshake(SINGLE_APP_ID)
    if not mh:
        return 0

    app_holder: List[Optional[WindowsOnTopApp]] = [None]
    first_quit = {"done": False}

    def on_pipe_quit() -> None:
        if first_quit["done"]:
            return
        first_quit["done"] = True
        app = app_holder[0]
        if app is not None:
            app.schedule_quit_from_pipe()

    bm_single_instance.start_pipe_server(SINGLE_APP_ID, on_pipe_quit)

    app = WindowsOnTopApp(mh)
    app_holder[0] = app
    app.maybe_start_minimized()
    if not (app._data.get("settings") or {}).get("auto_minimize"):                
        app.root.deiconify()
        app.root.lift()
        try:
            app.root.focus_force()
        except tk.TclError:
            pass

    app.run()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as ex:
        if getattr(sys, "frozen", False):
            try:
                logp = os.path.join(
                    os.environ.get("TEMP") or os.environ.get("TMP", "."),
                    "bm-windows-on-top.log",
                )
                with open(logp, "a", encoding="utf-8") as flog:
                    import traceback

                    flog.write(traceback.format_exc())
                    flog.write(str(ex) + "\n")
            except Exception:
                pass
        sys.exit(1)

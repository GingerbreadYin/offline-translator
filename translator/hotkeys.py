"""Windows global shortcut registration, transactional updates."""
import ctypes
from .core import validate_bindings


def parse_hotkey(binding):
    parts = binding.split("+")
    modifiers = 0
    for part in parts[:-1]:
        try:
            modifiers |= {"ctrl": 2, "alt": 1, "shift": 4, "win": 8, "meta": 8}[part.lower()]
        except KeyError as exc:
            raise ValueError(f"不支持的修饰键：{part}") from exc
    key = parts[-1].upper()
    special = {"UP": 38, "DOWN": 40, "LEFT": 37, "RIGHT": 39,
               "SPACE": 32, "TAB": 9, "ENTER": 13, "RETURN": 13,
               "BACKSPACE": 8, "DELETE": 46, "DEL": 46, "INSERT": 45,
               "INS": 45, "HOME": 36, "END": 35, "PGUP": 33, "PGDOWN": 34,
               "PAGEUP": 33, "PAGEDOWN": 34, ";": 186, "=": 187, ",": 188,
               "-": 189, ".": 190, "/": 191, "`": 192, "[": 219, "\\": 220,
               "]": 221, "'": 222, "PAUSE": 19, "SCROLLLOCK": 145, "CAPSLOCK": 20,
               "PRINT": 44, "PRINTSCREEN": 44}
    if len(key) == 1 and key.isascii() and key.isalnum():
        vk = ord(key)
    elif key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 111 + int(key[1:])
    elif key in special:
        vk = special[key]
    else:
        raise ValueError(f"该按键暂不支持绑定：{key}")
    return modifiers, vk


class Win32Backend:
    def register(self, id_, modifiers, key):
        return bool(ctypes.windll.user32.RegisterHotKey(None, id_, modifiers | 0x4000, key))

    def unregister(self, id_):
        ctypes.windll.user32.UnregisterHotKey(None, id_)


class Hotkeys:
    def __init__(self, backend=None):
        self.backend = backend or Win32Backend()
        self.bindings = []

    def apply(self, bindings):
        validate_bindings(bindings)
        parsed = [parse_hotkey(b) for b in bindings]
        if len(set(parsed)) != 3:
            raise ValueError("三个快捷键不能重复")
        previous = self.bindings[:]
        self.close()
        registered = []
        for i, (modifiers, key) in enumerate(parsed):
            if not self.backend.register(100 + i, modifiers, key):
                for id_ in registered:
                    self.backend.unregister(id_)
                restored = True
                for j, old in enumerate(previous):
                    restored = self.backend.register(100 + j, *parse_hotkey(old)) and restored
                self.bindings = previous if restored else []
                if not restored:
                    for j in range(3):
                        self.backend.unregister(100 + j)
                detail = "已保留原绑定" if restored else "原绑定也无法恢复，请重新设置"
                raise ValueError(f"快捷键 {bindings[i]} 被占用或受系统限制；{detail}")
            registered.append(100 + i)
        self.bindings = bindings[:]

    def close(self):
        for i in range(len(self.bindings)):
            self.backend.unregister(100 + i)
        self.bindings = []

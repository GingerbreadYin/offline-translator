import pytest
from translator.hotkeys import Hotkeys, parse_hotkey


def test_supported_keys_and_invalid_modifier_only():
    assert parse_hotkey("Ctrl+Alt+Q") == (3, 81)
    assert parse_hotkey("F8") == (0, 119)
    assert parse_hotkey("Ctrl+Alt+Up") == (3, 38)
    assert parse_hotkey(";") == (0, 186)
    with pytest.raises(ValueError):
        parse_hotkey("Ctrl")


def test_registration_failure_restores_previous_bindings():
    class Backend:
        def __init__(self):
            self.active = {}
        def register(self, id_, modifiers, key):
            if key == 120:  # occupied F9
                return False
            self.active[id_] = (modifiers, key)
            return True
        def unregister(self, id_):
            self.active.pop(id_, None)
    backend = Backend()
    keys = Hotkeys(backend)
    keys.apply(["F5", "F6", "F7"])
    with pytest.raises(ValueError):
        keys.apply(["F8", "F9", "F10"])
    assert backend.active == {100: (0, 116), 101: (0, 117), 102: (0, 118)}
    keys.close()
    assert backend.active == {}

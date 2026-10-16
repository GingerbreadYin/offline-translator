"""UI-independent state, dictionary results and settings."""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re

DEFAULT_BINDINGS = ("CapsLock", ",", ".", "Ctrl+Q")
LEGACY_DEFAULT_BINDINGS = ("Ctrl+Alt+Q", "Ctrl+Alt+Up", "Ctrl+Alt+Down")


def default_settings():
    return {"bindings": list(DEFAULT_BINDINGS), "schema_version": 2}


@dataclass(frozen=True)
class Meaning:
    pos: str
    text: str


@dataclass
class Result:
    original: str
    meanings: list[Meaning] = field(default_factory=list)
    translation: str = ""


def parse_meanings(value: str) -> list[Meaning]:
    result = []
    for line in value.splitlines():
        match = re.match(r"^\s*((?:[a-z]+\.){1,3})\s*(.*)$", line, re.I)
        pos, body = (match.group(1), match.group(2)) if match else ("", line)
        depth, start = 0, 0
        for index, char in enumerate(body + ","):
            if char in "(（[【":
                depth += 1
            elif char in ")）]】":
                depth = max(0, depth - 1)
            if char in ",，;；" and depth == 0:
                text = body[start:index].strip()
                if text and Meaning(pos, text) not in result:
                    result.append(Meaning(pos, text))
                start = index + 1
    return result


class Navigator:
    def __init__(self, meanings):
        self.meanings = meanings
        self.index = 0

    @property
    def current(self):
        return self.meanings[self.index] if self.meanings else None

    def move(self, delta):
        if self.meanings:
            self.index = (self.index + delta) % len(self.meanings)
        return self.current


class Workflow:
    def __init__(self):
        self.state = "idle"
        self.generation = 0

    def toggle(self):
        self.generation += 1
        self.state = "selecting" if self.state == "idle" else "idle"

    def cancel(self):
        self.generation += 1
        self.state = "idle"

    def begin(self):
        if self.state != "selecting":
            raise ValueError("No selection in progress")
        self.state = "processing"
        return self.generation

    def finish(self, generation):
        if generation != self.generation or self.state != "processing":
            return False
        self.state = "showing"
        return True


def place_result(selection, size, area):
    sx, sy, sw, sh = selection
    ax, ay, aw, ah = area
    width, height = min(size[0], aw), min(size[1], ah)
    x = max(ax, min(sx, ax + aw - width))
    y = sy - height - 8
    if y < ay:
        y = sy + sh + 8
    y = max(ay, min(y, ay + ah - height))
    return x, y, width, height


def validate_bindings(bindings):
    if not isinstance(bindings, list) or len(bindings) != 4 or not all(isinstance(b, str) for b in bindings) or len({b.lower() for b in bindings}) != 4:
        raise ValueError("四个快捷键不能为空或重复")
    for binding in bindings:
        parts = binding.split("+")
        if not binding or parts[-1].lower() in {"ctrl", "alt", "shift", "win", "meta", "esc", "escape"}:
            raise ValueError("请选择有效单键或组合键；Esc保留用于取消")


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self):
        if not self.path.exists():
            return default_settings()
        try:
            settings = json.loads(self.path.read_text(encoding="utf-8"))
            bindings = settings["bindings"]
            if isinstance(bindings, list) and len(bindings) == 3 and all(isinstance(b, str) for b in bindings):
                if [b.lower() for b in bindings] == [b.lower() for b in LEGACY_DEFAULT_BINDINGS]:
                    settings = default_settings()
                else:
                    occupied = {b.lower() for b in bindings}
                    toggle = next(b for b in ("Ctrl+Q", "Ctrl+Alt+S", "Ctrl+Alt+F12", "Ctrl+Alt+F11") if b.lower() not in occupied)
                    settings = {"bindings": bindings + [toggle], "schema_version": 2}
            validate_bindings(settings["bindings"])
            return settings
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("设置文件损坏，请备份后删除 settings.json") from exc

    def save(self, settings):
        validate_bindings(settings["bindings"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

"""Pure paragraph and layout policies for visible-window translation."""
from dataclasses import dataclass
import re
from .core import Result


@dataclass
class Paragraph:
    text: str
    rect: tuple


@dataclass
class TranslatedParagraph:
    rect: tuple
    result: Result


def bounds(points):
    xs, ys = [float(p[0]) for p in points], [float(p[1]) for p in points]
    x, y = int(min(xs)), int(min(ys))
    return x, y, max(1, int(max(xs))-x), max(1, int(max(ys))-y)


def intersects(a, b):
    return a[0] < b[0]+b[2] and b[0] < a[0]+a[2] and a[1] < b[1]+b[3] and b[1] < a[1]+a[3]


def group_lines(lines):
    candidates = []
    for polygon, text, confidence in lines:
        text = text.strip()
        if float(confidence) < .5 or not re.search('[A-Za-z]', text):
            continue
        if re.fullmatch(r'(?:https?://|www\.)\S+', text, re.I):
            continue
        if re.search(r'(^\s*(?:const|let|var|import|from|def|class|return)\s|[{}]|[=;].*[();])', text):
            continue
        if text.lower() in {'file','edit','view','help','settings','share','search','code','issues','pull requests','sign in','sign up'}:
            continue
        rect = bounds(polygon)
        if rect[3] < 10:
            continue
        candidates.append(Paragraph(text, rect))
    candidates.sort(key=lambda p: (p.rect[1], p.rect[0]))
    groups = []
    for line in candidates:
        x, y, w, h = line.rect
        group = None
        for previous in reversed(groups):
            px, py, pw, ph = previous.rect
            gap = y-(py+ph)
            overlap = min(x+w, px+pw)-max(x,px)
            if 0 <= gap <= h*.9 and overlap >= min(w,pw)*.4 and abs(x-px) <= max(35, h*2) and len(previous.text)+len(line.text) < 1800:
                group = previous
                break
        if group:
            px, py, pw, ph = group.rect
            group.text += ' ' + line.text
            group.rect = (min(x,px), py, max(x+w,px+pw)-min(x,px), y+h-py)
        else:
            groups.append(line)
    return groups


def place_translations(originals, sizes, area, obstacles=None):
    ax, ay, aw, ah = area
    occupied = list(originals if obstacles is None else obstacles)
    placements = []
    for rect, size in zip(originals, sizes):
        x, y, w, h = rect
        width, height = min(size[0], aw), size[1]
        candidate = (max(ax,min(x,ax+aw-width)), y-height-8, width,height)
        if candidate[1] >= ay and candidate[1]+height <= ay+ah and not any(intersects(candidate, other) for other in occupied):
            placements.append(candidate)
            occupied.append(candidate)
        else:
            placements.append(None)
    return placements

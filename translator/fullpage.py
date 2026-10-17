"""Pure paragraph, layout and refresh policies for visible-window translation."""
from dataclasses import dataclass
from hashlib import blake2b
import re
from PIL import ImageChops
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


class RefreshGate:
    def __init__(self, stable_seconds=.65):
        self.stable_seconds = stable_seconds
        self.signature = None
        self.changed_at = 0
        self.submitted = False
        self.previous = None
        self.recent = []
        self.last_pixel_change = 0

    def reset(self):
        self.signature = None
        self.submitted = False
        self.previous = None
        self.recent = []

    def observe(self, image, focused, now):
        if not focused:
            self.reset()
            return 'hidden'
        signature = (image.size, blake2b(image.tobytes(), digest_size=16).digest())
        if signature != self.signature:
            box = ImageChops.difference(image,self.previous).getbbox() if self.previous is not None and self.previous.size == image.size else None
            # Recognize a recurring, localized vertical caret blink. A first
            # change (even one pixel) still invalidates; new text never relies
            # on a downscaled hash which could silently miss a changed word.
            caret = (box is not None and box[2]-box[0] <= 4 and box[3]-box[1] <= 80
                     and signature in self.recent and now-self.last_pixel_change <= 1.2)
            self.last_pixel_change = now
            self.signature = signature
            self.previous = image.copy()
            self.recent = (self.recent+[signature])[-8:]
            if not caret:
                self.changed_at, self.submitted = now, False
                return 'changed'
        if not self.submitted and now-self.changed_at >= self.stable_seconds:
            self.submitted = True
            return 'ready'
        return 'unchanged' if self.submitted else 'waiting'

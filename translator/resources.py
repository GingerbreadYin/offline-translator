import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_resources(root):
    root = Path(root)
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        entries = manifest["files"]
        if not entries:
            return ["manifest.json"]
    except (OSError, ValueError, KeyError):
        return ["manifest.json"]
    invalid = []
    for entry in entries:
        path = (root / entry["path"]).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or sha256(path) != entry["sha256"]:
            invalid.append(entry["path"])
    return invalid

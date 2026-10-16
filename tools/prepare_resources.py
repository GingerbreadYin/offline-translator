"""Explicit build-time resource download/import; never imported for network by UI."""
import argparse
from contextlib import closing
import csv
import json
import os
from pathlib import Path
import sqlite3
import urllib.request
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translator.resources import sha256

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "ecdict.csv": "https://raw.githubusercontent.com/skywind3000/ECDICT/bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b/ecdict.csv",
    "en_zh.argosmodel": "https://argos-net.com/v1/translate-en_zh-1_9.argosmodel",
}


def build_dictionary(source, destination):
    temporary = destination.with_suffix(".tmp")
    if temporary.exists():
        temporary.unlink()
    with closing(sqlite3.connect(temporary)) as db, source.open(encoding="utf-8", newline="") as stream:
        db.execute("CREATE TABLE words(word TEXT PRIMARY KEY, translation TEXT, exchange TEXT)")
        db.execute("CREATE TABLE forms(form TEXT, lemma TEXT, PRIMARY KEY(form,lemma))")
        for row in csv.DictReader(stream):
            word = row["word"].strip().lower()
            translation = row.get("translation", "").replace("\\n", "\n")
            exchange = row.get("exchange", "")
            if not word or not translation:
                continue
            db.execute("INSERT OR IGNORE INTO words VALUES (?,?,?)", (word, translation, exchange))
            for item in exchange.split("/"):
                kind, _, form = item.partition(":")
                if kind in {"p", "d", "i", "3", "r", "t", "s"} and form:
                    db.execute("INSERT OR IGNORE INTO forms VALUES (?,?)", (form.lower(), word))
                elif kind == "0" and form:
                    db.execute("INSERT OR IGNORE INTO forms VALUES (?,?)", (word, form.lower()))
        db.commit()
    os.replace(temporary, destination)


def extract_translation(source, destination):
    with zipfile.ZipFile(source) as archive:
        selected = []
        for name in archive.namelist():
            relative = Path(*name.split("/")[1:])
            if ".." in relative.parts or relative.is_absolute():
                raise ValueError("Unsafe archive path")
            if not name.endswith("/") and (relative.parts and relative.parts[0] == "model" or str(relative) in {"sentencepiece.model", "metadata.json", "README.md"}):
                selected.append((name, relative))
        for name, relative in selected:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))


def prepare(download=False):
    root = ROOT / "resources"
    root.mkdir(exist_ok=True)
    original = {}
    if (root / "manifest.json").exists():
        original = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    source_entries = []
    for filename, url in SOURCES.items():
        destination = root / filename
        expected = next((s.get("sha256") for s in original.get("sources", []) if s["name"] == filename), None)
        if not destination.exists():
            if not download:
                raise FileNotFoundError(f"Missing {filename}; use --download explicitly")
            temp = destination.with_suffix(".download")
            print(f"Downloading {filename}", flush=True)
            urllib.request.urlretrieve(url, temp)
            if expected and sha256(temp) != expected:
                raise ValueError(f"Source checksum mismatch: {filename}")
            os.replace(temp, destination)
        if expected and sha256(destination) != expected:
            raise ValueError(f"Source checksum mismatch: {filename}")
        source_entries.append({"name": filename, "url": url, "sha256": sha256(destination), "bytes": destination.stat().st_size})
    print("Importing dictionary", flush=True)
    build_dictionary(root / "ecdict.csv", root / "dictionary.db")
    extract_translation(root / "en_zh.argosmodel", root / "translation")
    files = [root / "dictionary.db", *sorted((root / "translation").rglob("*"))]
    manifest = {"version": "0.1.0", "sources": source_entries, "files": [
        {"path": file.relative_to(root).as_posix(), "sha256": sha256(file), "bytes": file.stat().st_size} for file in files if file.is_file()
    ]}
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Resources prepared", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    prepare(parser.parse_args().download)

"""Local-only service adapters. No network access at runtime."""
from pathlib import Path
from contextlib import closing
import re
import sqlite3
import threading
from .core import Result, parse_meanings


class Dictionary:
    def __init__(self, path):
        self.path = Path(path)

    def find(self, word):
        word = word.lower().strip()
        with closing(sqlite3.connect(f"file:{self.path.as_posix()}?mode=ro", uri=True)) as db:
            row = db.execute("SELECT translation FROM words WHERE word=?", (word,)).fetchone()
            if not row:
                row = db.execute("SELECT w.translation FROM forms f JOIN words w ON w.word=f.lemma WHERE f.form=? LIMIT 1", (word,)).fetchone()
        return parse_meanings(row[0]) if row and row[0] else []


class Lookup:
    def __init__(self, dictionary, translator):
        self.dictionary = dictionary
        self.translator = translator

    def lookup(self, text):
        text = text.strip()
        if not text or not re.search(r"[A-Za-z]", text):
            raise ValueError("未识别到英文，请重新框选")
        if len(text) > 2000:
            raise ValueError("第一版支持短文本，请框选不超过2000个字符")
        word = text.strip(" \t\n.,;:!?\"“”()[]")
        if re.fullmatch(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", word):
            meanings = self.dictionary.find(word)
            if meanings:
                return Result(word, meanings)
        return Result(text, translation=self.translator.translate(text))


class OfflineTranslator:
    def __init__(self, root):
        self.root = Path(root)
        self.engine = None

    def translate(self, text):
        if self.engine is None:
            import ctranslate2
            import sentencepiece
            tokenizer = sentencepiece.SentencePieceProcessor(model_proto=(self.root / "sentencepiece.model").read_bytes())
            engine = ctranslate2.Translator(str(self.root / "model"), device="cpu", compute_type="int8", inter_threads=1, intra_threads=4)
            self.tokenizer, self.engine = tokenizer, engine
        # Preserve explicit links and code spans without sending them through translation.
        chunks = re.split(r"(https?://[^\s]+|`[^`]+`)", text)
        outputs = []
        for index, chunk in enumerate(chunks):
            if index % 2 or not chunk.strip():
                outputs.append(chunk)
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", chunk) if s.strip()]
            tokens = [self.tokenizer.encode(s, out_type=str) for s in sentences]
            translated = self.engine.translate_batch(tokens, beam_size=4, max_decoding_length=512, replace_unknowns=True, length_penalty=0.2)
            outputs.append(" ".join(self.tokenizer.decode(r.hypotheses[0]).replace("▁", " ").strip() for r in translated))
        return "".join(outputs).strip()


class Pipeline:
    def __init__(self, resource_root):
        self.root = Path(resource_root)
        self.lookup = Lookup(Dictionary(self.root / "dictionary.db"), OfflineTranslator(self.root / "translation"))
        self.ocr = None
        self.lock = threading.Lock()
        self.verified = False

    def recognize(self, image):
        if self.ocr is None:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr = RapidOCR(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False, intra_op_num_threads=4)
        import numpy as np
        data = np.array(image.convert("RGB"))[:, :, ::-1].copy()
        result, _ = self.ocr(data)
        if not result:
            raise ValueError("未识别到英文，请重新框选")
        return "\n".join(item[1] for item in result)

    def run(self, image):
        with self.lock:
            if not self.verified:
                from .resources import verify_resources
                invalid = verify_resources(self.root)
                if invalid:
                    raise ValueError("离线资源缺失或损坏，请重新解压完整发行包：" + ", ".join(invalid[:3]))
                self.verified = True
            return self.lookup.lookup(self.recognize(image))

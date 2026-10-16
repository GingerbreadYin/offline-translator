"""Real local-resource smoke check, also callable from packaged executable."""
import time
from PIL import Image, ImageDraw, ImageFont
from translator.resources import verify_resources
from translator.services import Pipeline


def probe(root):
    invalid = verify_resources(root)
    if invalid:
        raise RuntimeError("资源缺失或损坏：" + ", ".join(invalid))
    pipeline = Pipeline(root)
    results = []
    for sample in ["issue", "This project is open source.", "Please open the settings window."]:
        image = Image.new("RGB", (850, 100), "white")
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 32)
        ImageDraw.Draw(image).text((20, 28), sample, fill="black", font=font)
        started = time.perf_counter()
        recognized = pipeline.recognize(image)
        result = pipeline.lookup.lookup(recognized)
        elapsed = round(time.perf_counter()-started, 3)
        if sample == "issue":
            if recognized.lower().strip() != "issue" or not result.meanings:
                raise AssertionError("OCR/dictionary integration failed")
        elif not result.translation or not any("\u4e00" <= c <= "\u9fff" for c in result.translation):
            raise AssertionError("Translation did not produce Chinese")
        results.append({"input": sample, "ocr": recognized, "result": (result.meanings[0].pos + " " + result.meanings[0].text) if result.meanings else result.translation, "seconds": elapsed})
        image.close()
    return {"offline": True, "fixtures": "synthetic screen text; real manga not yet tested", "samples": results}

# Third-party notices

This application reuses the following projects. No ownership of their code, data, or models is claimed.

| Component | Origin | License / attribution |
|---|---|---|
| RapidOCR Python interface and packaged OCR models | https://github.com/RapidAI/RapidOCR | Apache-2.0 project; packaged PP-OCR models originate from PaddleOCR https://github.com/PaddlePaddle/PaddleOCR (Apache-2.0) |
| English-Chinese dictionary | https://github.com/skywind3000/ECDICT | MIT; source revision bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b. CSV converted into local SQLite; original dictionary order retained |
| English-Chinese language package 1.9 | https://github.com/argosopentech/argospm-index | Packaged by Argos Translate; package README attributes original OPUS-MT model to Jörg Tiedemann and Santhosh Thottingal, CC-BY 4.0. We extract the CTranslate2 model and SentencePiece tokenizer, omit unused Stanza data, and apply int8 CPU inference |
| OPUS-MT reference | https://github.com/Helsinki-NLP/Opus-MT | Tiedemann and Thottingal (2020), “OPUS-MT — Building open translation services for the World”, EAMT, Lisbon |
| CTranslate2 | https://github.com/OpenNMT/CTranslate2 | MIT |
| SentencePiece | https://github.com/google/sentencepiece | Apache-2.0 |
| PySide6 / Qt | https://www.qt.io/qt-for-python | LGPLv3 / GPLv3 / commercial options; dynamically loaded libraries are distributed in the portable folder. Qt licensing information: https://www.qt.io/licensing/open-source-lgpl-obligations ; source: https://code.qt.io/ and https://download.qt.io/official_releases/ |
| ONNX Runtime | https://github.com/microsoft/onnxruntime | MIT |
| Python | https://www.python.org/ | Python Software Foundation License |
| PyInstaller | https://github.com/pyinstaller/pyinstaller | GPL with bootloader distribution exception; build tool |

The portable distribution includes `licenses/` with the installed distributions' license files and Python license. The translation resource includes its original attribution README. See `requirements.lock.txt` for dependency versions and `resources/manifest.json` for source URLs, hashes and generated resource files.

ECDICT is an aggregated dictionary dataset. Its repository license is retained; original source provenance described by that repository should be reviewed before broader public redistribution.

License information for transitive components is preserved in `licenses/`. This repository contains our integration code and tests; large third-party resource binaries are excluded from Git and distributed in the private release package for this personal-use first version.

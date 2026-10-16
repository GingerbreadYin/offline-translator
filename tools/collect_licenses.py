import importlib.metadata
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1]) / "licenses"
target.mkdir(exist_ok=True)
for dist in importlib.metadata.distributions():
    for file in dist.files or []:
        if any(term in file.name.lower() for term in ("license", "copying", "notice")) and not str(file).startswith(".."):
            source = Path(dist.locate_file(file))
            if source.is_file():
                destination = target / dist.metadata["Name"] / str(file).replace("/", "_").replace("\\", "_")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, target / "Python-LICENSE.txt")
local = Path(__file__).resolve().parents[1] / "licenses"
if local.exists():
    shutil.copytree(local, target, dirs_exist_ok=True)

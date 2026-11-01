"""Build the Windows x64 ZIP; only the build machine needs Python/pip and internet."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VERSION = "3.13.14"
RUNTIME_URL = f"https://www.python.org/ftp/python/{VERSION}/python-{VERSION}-embed-amd64.zip"
RUNTIME_SHA256 = "90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907"
SCRIPTS = (
    "decode_cfg.py", "decode_language_pack.py", "extract_config_pack.py",
    "extract_hero_images.py", "export_client_asset.py", "audit_native_client.py",
    "probe_metadata_patterns.py", "trace_native_file.py", "unpack_client_lzma.py",
    "test_client_inspection.py",
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(output, cache):
    if output.exists():
        raise ValueError("Use a new archive filename; existing packages are not overwritten")
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / f"python-{VERSION}-embed-amd64.zip"
    if not archive.exists():
        urllib.request.urlretrieve(RUNTIME_URL, archive)
    if digest(archive) != RUNTIME_SHA256:
        raise ValueError("Embedded Python download checksum mismatch")
    wheels = cache / "wheels"
    wheels.mkdir(exist_ok=True)
    lock = HERE / "requirements-lock.txt"
    requirements = lock if lock.exists() else HERE / "requirements.txt"
    subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                    "--platform", "win_amd64", "--python-version", "3.13", "--implementation", "cp",
                    "--abi", "cp313", "--find-links", str(HERE / "vendor"),
                    "--dest", str(wheels), "-r", str(requirements),
                    *(["--require-hashes"] if lock.exists() else [])], check=True)
    # Each build uses a fresh staging directory; never include repo extracts or local environments.
    staging = Path(tempfile.mkdtemp(prefix="stage-", dir=cache))
    package = staging / "Tiles-Survive-Extraction-Kit"
    runtime = package / "runtime"
    runtime.mkdir(parents=True)
    with zipfile.ZipFile(archive) as embedded:
        embedded.extractall(runtime)
    (runtime / "python313._pth").write_text(
        "python313.zip\n.\n../lib\n../tools\n..\n", encoding="ascii")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", str(wheels),
                    "--only-binary=:all:", "--platform", "win_amd64", "--python-version", "3.13",
                    "--implementation", "cp", "--abi", "cp313", "--no-compile",
                    "--target", str(package / "lib"), "-r", str(requirements),
                    *(["--require-hashes"] if lock.exists() else [])], check=True)
    (package / "tools").mkdir()
    for name in SCRIPTS:
        shutil.copy2(REPO / "work/hero-extraction" / name, package / "tools" / name)
    for name in ("kit.py", "Extract.cmd", "README.md", "requirements.txt", "test_kit.py", "build.py"):
        shutil.copy2(HERE / name, package / name)
    shutil.copytree(HERE / "vendor", package / "vendor")
    shutil.copy2(REPO / "docs/research/CLIENT-EXTRACTION-TOOLS.md", package / "ADVANCED-NOTES.md")
    # Freeze all resolved transitive wheels, preserving their bundled license metadata.
    resolved = []
    for dist in sorted((package / "lib").glob("*.dist-info")):
        metadata = (dist / "METADATA").read_text(encoding="utf-8")
        name = next(line[6:] for line in metadata.splitlines() if line.startswith("Name: "))
        version = next(line[9:] for line in metadata.splitlines() if line.startswith("Version: "))
        matches = [p for p in wheels.glob("*.whl")
                   if p.name.split("-")[0].lower().replace("_", "-") == name.lower().replace("_", "-")
                   and p.name.split("-")[1] == version]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one resolved wheel for {name}=={version}")
        resolved.append(f"{name}=={version} --hash=sha256:{digest(matches[0])}")
    (package / "requirements-lock.txt").write_text("\n".join(resolved) + "\n", encoding="utf-8")
    manifest = {"format": 1, "target": "Windows x64", "runtime_url": RUNTIME_URL,
                "runtime_archive_sha256": RUNTIME_SHA256, "files": [
                    {"path": p.relative_to(package).as_posix(), "sha256": digest(p)}
                    for p in sorted(package.rglob("*")) if p.is_file()]}
    (package / "package-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for arguments in (["kit.py", "doctor"], ["kit.py", "verify"],
                      ["-m", "unittest", "discover", "-s", "tools", "-p", "test_client_inspection.py"],
                      ["-m", "unittest", "test_kit"]):
        subprocess.run([str(runtime / "python.exe"), "-B", *arguments], cwd=package, check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                zipped.write(path, path.relative_to(staging))
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest(output)}  {output.name}\n", encoding="ascii")
    print(f"Package: {output}\nStaged folder: {package}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=REPO / "tmp/extraction-kit-build")
    args = parser.parse_args()
    build(args.output.resolve(), args.cache.resolve())

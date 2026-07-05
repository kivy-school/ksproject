#!/usr/bin/env python3
"""Build & package CPython-for-Android wheels for anaconda.org/kivyschool.

Modeled after BeeWare's ``libffi`` channel: one wheel per ABI, tagged with a
PEP 425 platform string like ``android_21_arm64_v8a``. Each wheel ships the
cross-build prefix verbatim plus the (ABI-independent) pure-Python stdlib, so
a consumer can extract it and use it directly in place of
``install_cpython_android()``.

  payload layout inside the wheel:
    libpython/prefix/<abi>/lib/libpython3.<minor>.so
    libpython/prefix/<abi>/lib/python3.<minor>/lib-dynload/<module>.so
    libpython/prefix/<abi>/include/python3.<minor>/...    (pyconfig.h is per-ABI)
    libpython/stdlib/python3.<minor>/<py-stdlib-tree>     (.py source, no .pyc)

  filename:
    libpython-<ver>-<rev>-py3-none-android_<api>_<abi_underscored>.whl

Strip note: an unstripped libpython3.13.so is ~24 MB; ~19 MB is ``.debug_*``.
``llvm-strip --strip-unneeded`` brings it to ~5 MB without rebuilding.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

# Allow running this script directly without installing the package.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ksproject_utils.gradle.cpython_android import (  # noqa: E402
    ANDROID_VERSION,
    _TRIPLES,
    android_prefix,
    install_cpython_android,
)

DEFAULT_ANDROID_API = 21
DIST_NAME = "libpython"

# Stdlib dirs/files we never ship. Version-specific config-3.X dirs are
# added per-run in collect_stdlib().
STDLIB_EXCLUDE_DIRS = {
    "lib-dynload",
    "site-packages",
    "test",
    "tests",
    "idlelib",
    "tkinter",
    "turtledemo",
    "ensurepip",
    "__pycache__",
}


def find_ndk(sdk: Path) -> Path | None:
    ndk_root = sdk / "ndk"
    if not ndk_root.is_dir():
        return None
    versions = sorted([p for p in ndk_root.iterdir() if p.is_dir()])
    return versions[-1] if versions else None


def host_tag() -> str:
    if sys.platform == "darwin":
        return "darwin-x86_64"
    if sys.platform.startswith("linux"):
        return "linux-x86_64"
    raise SystemExit(f"Unsupported host: {sys.platform}")


def llvm_tool(ndk: Path, name: str) -> Path:
    return ndk / "toolchains" / "llvm" / "prebuilt" / host_tag() / "bin" / name


def inspect(libpython: Path, ndk: Path) -> None:
    size = llvm_tool(ndk, "llvm-size")
    readelf = llvm_tool(ndk, "llvm-readelf")
    print(f"\n=== {libpython} ({libpython.stat().st_size / 1024 / 1024:.1f} MB) ===")
    subprocess.run([str(size), "-A", str(libpython)], check=False)
    print("\n--- sections ---")
    subprocess.run([str(readelf), "-S", str(libpython)], check=False)
    print("\n--- needed ---")
    out = subprocess.run(
        [str(readelf), "-d", str(libpython)], capture_output=True, text=True
    )
    for line in out.stdout.splitlines():
        if "NEEDED" in line:
            print(line)


def strip_lib(lib: Path, ndk: Path | None) -> None:
    if ndk is None:
        # No NDK available; official python.org binaries ship pre-stripped.
        return
    strip = llvm_tool(ndk, "llvm-strip")
    before = lib.stat().st_size
    subprocess.run([str(strip), "--strip-unneeded", str(lib)], check=True)
    after = lib.stat().st_size
    print(
        f"  stripped {lib.name}: "
        f"{before / 1024 / 1024:.2f} MB -> {after / 1024 / 1024:.2f} MB"
    )


def platform_tag(api: int, abi: str) -> str:
    # PEP 425 platform tag: hyphens become underscores.
    return f"android_{api}_{abi.replace('-', '_')}"


def collect_stdlib(prefix: Path, py_minor: str) -> list[Path]:
    # Build-config dirs are "config-3.X", "config-3.Xt" or, on Android,
    # "config-3.X-aarch64-linux-android" — match by prefix.
    config_prefix = f"config-{py_minor}"
    root = prefix / "lib" / f"python{py_minor}"
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(
            part in STDLIB_EXCLUDE_DIRS or part.startswith(config_prefix)
            for part in rel.parts
        ):
            continue
        if path.suffix in (".pyc", ".so"):
            continue
        out.append(path)
    return out


def _sha256_b64(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_wheel(
    out_dir: Path,
    version: str,
    rev: str,
    abi: str,
    api: int,
    prefix: Path,
    py_minor: str,
    ndk: Path | None,
) -> Path:
    tag = platform_tag(api, abi)
    wheel_name = f"{DIST_NAME}-{version}-{rev}-py3-none-{tag}.whl"
    wheel_path = out_dir / wheel_name
    dist_info = f"{DIST_NAME}-{version}.dist-info"

    # Stage stripped binaries in a scratch dir so we don't mutate the build tree.
    stage = out_dir / f"_stage_{abi}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # (src_path, arcname_inside_wheel)
    entries: list[tuple[Path, str]] = []

    # Runtime libs from prefix/lib: libpython plus the OpenSSL/SQLite deps
    # (and their _python-renamed variants) that lib-dynload modules link
    # against. Only libpython is mandatory.
    libpy_src = prefix / "lib" / f"libpython{py_minor}.so"
    if not libpy_src.exists():
        raise SystemExit(f"missing {libpy_src}")
    lib_names = [
        f"libpython{py_minor}.so",
        #"libcrypto.so",
        "libcrypto_python.so",
        "libsqlite3.so",
        "libsqlite3_python.so",
        "libssl.so",
        "libssl_python.so",
    ]
    for name in lib_names:
        src = prefix / "lib" / name
        if not src.exists():
            print(f"  note: {name} not present in prefix/lib, skipping")
            continue
        dst = stage / name
        shutil.copy2(src, dst)
        strip_lib(dst, ndk)
        entries.append((dst, f"libpython/prefix/{abi}/lib/{name}"))

    dynload_src = prefix / "lib" / f"python{py_minor}" / "lib-dynload"
    dynload_stage = stage / "lib-dynload"
    dynload_stage.mkdir()
    for so in sorted(dynload_src.glob("*.so")):
        dst = dynload_stage / so.name
        shutil.copy2(so, dst)
        strip_lib(dst, ndk)

    for so in sorted(dynload_stage.glob("*.so")):
        entries.append(
            (
                so,
                f"libpython/prefix/{abi}/lib/python{py_minor}/lib-dynload/{so.name}",
            )
        )

    # Per-ABI Python headers (pyconfig.h is arch-specific).
    include_root = prefix / "include" / f"python{py_minor}"
    if include_root.exists():
        for src in include_root.rglob("*"):
            if src.is_file():
                rel = src.relative_to(include_root)
                entries.append(
                    (
                        src,
                        f"libpython/prefix/{abi}/include/python{py_minor}/{rel.as_posix()}",
                    )
                )

    stdlib_root = prefix / "lib" / f"python{py_minor}"
    for src in collect_stdlib(prefix, py_minor):
        rel = src.relative_to(stdlib_root)
        entries.append((src, f"libpython/stdlib/python{py_minor}/{rel.as_posix()}"))

    metadata = (
        f"Metadata-Version: 2.1\n"
        f"Name: {DIST_NAME}\n"
        f"Version: {version}\n"
        f"Summary: CPython {version} runtime for Android ({abi}), incl. stdlib & lib-dynload.\n"
        f"Home-page: https://anaconda.org/kivyschool\n"
        f"License: PSF-2.0\n"
        f"Platform: Android\n"
        f"Requires-Python: =={py_minor}.*\n"
    ).encode("utf-8")
    wheel_meta = (
        f"Wheel-Version: 1.0\n"
        f"Generator: ksproject build_python_target.py\n"
        f"Root-Is-Purelib: false\n"
        f"Tag: py3-none-{tag}\n"
        f"Build: {rev}\n"
    ).encode("utf-8")

    out_dir.mkdir(parents=True, exist_ok=True)
    record_rows: list[tuple[str, str, int]] = []
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arc in entries:
            data = src.read_bytes()
            zf.writestr(arc, data)
            record_rows.append((arc, _sha256_b64(data), len(data)))

        def _add_dist_file(name: str, data: bytes) -> None:
            arc = f"{dist_info}/{name}"
            zf.writestr(arc, data)
            record_rows.append((arc, _sha256_b64(data), len(data)))

        _add_dist_file("METADATA", metadata)
        _add_dist_file("WHEEL", wheel_meta)

        # RECORD has no hash/size entry for itself.
        record_buf = io.StringIO()
        writer = csv.writer(record_buf, lineterminator="\n")
        for arc, digest, size in record_rows:
            writer.writerow([arc, digest, size])
        writer.writerow([f"{dist_info}/RECORD", "", ""])
        zf.writestr(f"{dist_info}/RECORD", record_buf.getvalue())

    shutil.rmtree(stage)
    print(
        f"  wrote {wheel_path.name} "
        f"({wheel_path.stat().st_size / 1024 / 1024:.2f} MB)"
    )
    return wheel_path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "version",
        nargs="?",
        default=None,
        help=f"CPython version (e.g. 3.13.11); defaults to {ANDROID_VERSION}",
    )
    ap.add_argument(
        "--version",
        dest="version_flag",
        default=None,
        help="CPython version (alternative to the positional argument)",
    )
    ap.add_argument("--rev", default="0", help="build-tag suffix (e.g. 0, 1, ...)")
    ap.add_argument(
        "--archs",
        default=",".join(_TRIPLES.keys()),
        help="comma-separated ABIs (default: arm64-v8a,x86_64)",
    )
    ap.add_argument(
        "--api",
        type=int,
        default=DEFAULT_ANDROID_API,
        help="min Android API level for the platform tag (default: 21)",
    )
    ap.add_argument(
        "--work-dir",
        type=Path,
        default=REPO_ROOT / ".build-target",
        help="scratch dir for the cross-build (holds .kivyschool/Python-<ver>/)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "dist" / "python-target",
        help="output directory for produced wheels",
    )
    ap.add_argument(
        "--sdk",
        default=os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT"),
        help="Android SDK root (must contain ndk/<ver>/)",
    )
    ap.add_argument("--ndk", default=os.environ.get("ANDROID_NDK_ROOT"))
    ap.add_argument("--java", default=os.environ.get("JAVA_HOME"))
    ap.add_argument(
        "--inspect-only",
        action="store_true",
        help="only run llvm-size/readelf on existing libpython, then exit",
    )
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="reuse existing cross-build artifacts in --work-dir",
    )
    args = ap.parse_args()

    version = args.version or args.version_flag or ANDROID_VERSION
    archs = [a.strip() for a in args.archs.split(",") if a.strip()]
    py_minor = ".".join(version.split(".")[:2])

    sdk_path = Path(args.sdk) if args.sdk else None
    ndk_path = Path(args.ndk) if args.ndk else (find_ndk(sdk_path) if sdk_path else None)
    if ndk_path is None:
        if args.inspect_only:
            raise SystemExit("--inspect-only needs an NDK (--sdk / --ndk)")
        print(
            "note: no Android SDK/NDK found — llvm-strip will be skipped "
            "(fine for official python.org binaries, which are pre-stripped); "
            "building from source is unavailable"
        )

    args.work_dir.mkdir(parents=True, exist_ok=True)
    ks_root = args.work_dir / ".kivyschool"

    if args.inspect_only:
        for arch in archs:
            pfx = android_prefix(ks_root, arch, version)
            lib = pfx / "lib" / f"libpython{py_minor}.so"
            if lib.exists():
                inspect(lib, ndk_path)
                return 0
        raise SystemExit("no libpython found to inspect")

    if not args.skip_build:
        install_cpython_android(
            ks_root=ks_root,
            archs=archs,
            sdk=str(sdk_path) if sdk_path else None,
            ndk=str(ndk_path) if ndk_path else None,
            java=args.java,
            py_version=py_minor,
            android_version=version,
        )

    out_root = args.out_dir / f"{version}-{args.rev}"
    out_root.mkdir(parents=True, exist_ok=True)

    for arch in archs:
        pfx = android_prefix(ks_root, arch, version)
        print(f"\n[{arch}] building wheel (api={args.api})")
        build_wheel(
            out_dir=out_root,
            version=version,
            rev=args.rev,
            abi=arch,
            api=args.api,
            prefix=pfx,
            py_minor=py_minor,
            ndk=ndk_path,
        )

    print(f"\nDone. Wheels in {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

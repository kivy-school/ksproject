"""Orchestrates Gradle project generation. Ported from GradleProjectBuilder.swift."""
from __future__ import annotations

import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from ..pyproject_toml import KivySchoolData, PyProjectToml
from .gradle_build_files import GradleBuildFiles
from .android_toolchain import AndroidToolchain
from .cpython_android import (
    ANDROID_VERSION,
    PY_VERSION,
    android_prefix,
    install_cpython_android,
)

Arch = KivySchoolData.AndroidData.Arch


class GradleProjectBuilder:

    def __init__(self, pyproject: PyProjectToml, working_dir: Path):
        self.pyproject = pyproject
        self.working_dir = working_dir

        kivy_school = pyproject.tool.kivy_school
        if kivy_school is None:
            raise ValueError("[tool.kivy-school] is missing in pyproject.toml")

        self.kivy_school = kivy_school
        self.android = kivy_school.android
        self.app_name = kivy_school.app_name or pyproject.project.name
        self.package_name = (
            self.android.package_name
            if self.android and self.android.package_name
            else f"org.kivyschool.{pyproject.project.name}"
        )
        self.archs: list[Arch] = (
            self.android.archs if self.android and self.android.archs
            else [Arch.ARM64_V8A, Arch.X86_64]
        )

    @classmethod
    def create(cls, uv_dir: Path) -> "GradleProjectBuilder":
        pyproject_path = uv_dir / "pyproject.toml"
        pyproject = PyProjectToml(str(pyproject_path))
        if pyproject.tool.kivy_school is None:
            raise ValueError("[tool.kivy-school] is missing")
        builder = cls(pyproject, uv_dir)
        builder.generate()
        return builder

    # ------------------------------------------------------------------
    # Asset resolution
    # ------------------------------------------------------------------

    def _resolve_asset(self, name: str) -> Path:
        """Return the path to a user-supplied asset or the bundled template fallback.

        ``name`` is e.g. ``"icon"`` — looks up ``android.icon`` in pyproject.toml
        and falls back to ``ksproject_utils/templates/<name>.png`` (then ``.jpg``).
        """
        user_value: str | None = (
            getattr(self.android, name, None) if self.android else None
        )
        if user_value:
            p = Path(user_value)
            if not p.is_absolute():
                p = self.working_dir / p
            return p
        templates = Path(__file__).parent.parent / "templates"
        for ext in ("png", "jpg"):
            candidate = templates / f"{name}.{ext}"
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            f"No template found for '{name}' in {templates}"
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, aar: bool = False) -> None:
        dist_dir = self.working_dir / "project_dist" / "gradle"
        dist_dir.mkdir(parents=True, exist_ok=True)

        # Resolve toolchain first — we need the SDK path for local.properties
        toolchain = AndroidToolchain.resolve(self.android, self.working_dir)

        # Root Gradle files
        GradleBuildFiles.write_root_build_gradle(dist_dir)
        GradleBuildFiles.write_settings_gradle(dist_dir, self.app_name)
        GradleBuildFiles.write_gradle_properties(dist_dir)
        GradleBuildFiles.write_local_properties(dist_dir, toolchain.sdk_path)

        # app module (must exist before `gradle wrapper` evaluates settings.gradle.kts)
        app_dir = dist_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        GradleBuildFiles.write_app_build_gradle(
            app_dir,
            package_name=self.package_name,
            archs=self.archs,
            compile_sdk=(self.android.api if self.android and self.android.api else 35),
            min_sdk=(self.android.min_api if self.android and self.android.min_api else 24),
            target_sdk=(self.android.api if self.android and self.android.api else 35),
            python_version=PY_VERSION,
            ndk_version=toolchain.ndk_version,
            ndk_path=toolchain.ndk_path,
            aar=aar,
            gradle_dependencies=(self.android.gradle_dependencies if self.android else []),
        )

        main_dir = app_dir / "src" / "main"
        main_dir.mkdir(parents=True, exist_ok=True)
        GradleBuildFiles.write_android_manifest(
            main_dir,
            package_name=self.package_name,
            app_name=self.app_name,
            permissions=(self.android.permissions if self.android else []),
            meta_data=(self.android.meta_data if self.android else {}),
        )
        res_dir = main_dir / "res"
        GradleBuildFiles.write_icon(res_dir, self._resolve_asset("icon"))
        GradleBuildFiles.write_main_activity(
            main_dir, self.package_name, PY_VERSION, self.pyproject.project.name
        )
        GradleBuildFiles.write_renpy_hardware(main_dir, self.package_name)
        GradleBuildFiles.write_kivy_python_activity(main_dir, self.package_name)
        _install_sdl2_java(main_dir, self.working_dir)
        _install_sdl2_headers(main_dir, self.working_dir)

        # Native bootstrap (libmain.so) — provides SDL_main → CPython
        cpp_dir = main_dir / "cpp"
        GradleBuildFiles.write_main_c(cpp_dir, PY_VERSION)
        GradleBuildFiles.write_cmake_lists(cpp_dir)

        # Generate the wrapper now that the app module exists on disk
        GradleBuildFiles.write_gradle_wrapper(dist_dir, toolchain.java_path)

        # Build CPython for Android (cached in .kivyschool/)
        install_cpython_android(
            working_dir=self.working_dir,
            archs=[a.value for a in self.archs],
            sdk=toolchain.sdk_path,
            ndk=toolchain.ndk_path,
            java=toolchain.java_path,
        )

        # Copy libpython + arch-specific extension modules to jniLibs per ABI
        for arch in self.archs:
            prefix = android_prefix(self.working_dir, arch.value)
            jni_abi = main_dir / "jniLibs" / arch.value
            jni_abi.mkdir(parents=True, exist_ok=True)

            src_lib = prefix / f"lib/libpython{PY_VERSION}.so"
            if src_lib.exists():
                dst_lib = jni_abi / "libpython3.so"
                if not dst_lib.exists():
                    shutil.copy2(src_lib, dst_lib)

            # Extension modules go into assets/lib-dynload/<abi> so they can be
            # unpacked to a writable filesystem path at runtime (AGP 8 keeps
            # native libs compressed inside the APK, and only files matching
            # lib*.so are exposed via nativeLibraryDir).
            lib_dynload = prefix / f"lib/python{PY_VERSION}/lib-dynload"
            if lib_dynload.exists():
                dynload_dst = (
                    main_dir / "assets" / "lib-dynload" / arch.value
                )
                dynload_dst.mkdir(parents=True, exist_ok=True)
                for so_file in lib_dynload.iterdir():
                    if so_file.suffix == ".so":
                        dst = dynload_dst / so_file.name
                        if not dst.exists():
                            shutil.copy2(so_file, dst)

            # Python headers for the native bootstrap (per-ABI: pyconfig.h differs)
            py_inc_src = prefix / f"include/python{PY_VERSION}"
            py_inc_dst = main_dir / "cpp" / "python_include" / arch.value
            if py_inc_src.exists() and not py_inc_dst.exists():
                shutil.copytree(py_inc_src, py_inc_dst)

        # Copy pure Python stdlib once (no .so, no lib-dynload)
        first_prefix = android_prefix(self.working_dir, self.archs[0].value)
        stdlib_src = first_prefix / f"lib/python{PY_VERSION}"
        assets_dir = main_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        stdlib_dst = assets_dir / f"python{PY_VERSION}"
        if not stdlib_dst.exists() and stdlib_src.exists():
            _copy_pure_python(stdlib_src, stdlib_dst)

        print(f"Gradle project generated at: {dist_dir}")
        print(f"  app/src/main/jniLibs/<abi> — libpython + extension .so per ABI")
        print(f"  app/src/main/assets/python{PY_VERSION}/ — pure Python stdlib")
        print(
            "  site-packages copied at build time via Gradle "
            "copySitePackagesToAssets task"
        )
        print("")
        print(f"Build with: cd {dist_dir} && ./gradlew assembleDebug")


_SDL2_VERSION = "2.30.11"
_SDL2_JAVA_PREFIX = f"SDL2-{_SDL2_VERSION}/android-project/app/src/main/java/org/libsdl/app/"
_SDL2_INCLUDE_PREFIX = f"SDL2-{_SDL2_VERSION}/include/"
_SDL2_TARBALL_URL = (
    f"https://github.com/libsdl-org/SDL/releases/download/"
    f"release-{_SDL2_VERSION}/SDL2-{_SDL2_VERSION}.tar.gz"
)


def _sdl2_cache_root(working_dir: Path) -> Path:
    return working_dir / ".kivyschool" / f"sdl2-{_SDL2_VERSION}"


def _populate_sdl2_cache(working_dir: Path) -> None:
    """Download SDL2 source tarball once and extract Java + include/ to cache."""
    cache = _sdl2_cache_root(working_dir)
    java_cache = cache / "java"
    include_cache = cache / "include"
    if java_cache.exists() and include_cache.exists():
        return
    cache.mkdir(parents=True, exist_ok=True)
    java_cache.mkdir(parents=True, exist_ok=True)
    include_cache.mkdir(parents=True, exist_ok=True)
    print(f"[ksproject] Downloading SDL2 {_SDL2_VERSION} source...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tarball = Path(tmpdir) / f"SDL2-{_SDL2_VERSION}.tar.gz"
        urllib.request.urlretrieve(_SDL2_TARBALL_URL, tarball)
        with tarfile.open(tarball, "r:gz") as tar:
            for member in tar.getmembers():
                if member.isdir():
                    continue
                if (
                    member.name.startswith(_SDL2_JAVA_PREFIX)
                    and member.name.endswith(".java")
                ):
                    filename = member.name[len(_SDL2_JAVA_PREFIX):]
                    f = tar.extractfile(member)
                    if f is not None:
                        (java_cache / filename).write_bytes(f.read())
                elif (
                    member.name.startswith(_SDL2_INCLUDE_PREFIX)
                    and member.name.endswith(".h")
                ):
                    rel = member.name[len(_SDL2_INCLUDE_PREFIX):]
                    dst = include_cache / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    f = tar.extractfile(member)
                    if f is not None:
                        dst.write_bytes(f.read())
    print(f"[ksproject] SDL2 source cached at {cache}")


def _install_sdl2_java(main_dir: Path, working_dir: Path) -> None:
    """Copy SDL2 Java source files (SDLActivity etc) into src/main/java/org/libsdl/app/."""
    dest_dir = main_dir / "java" / "org" / "libsdl" / "app"
    if dest_dir.exists() and any(f.suffix == ".java" for f in dest_dir.iterdir()):
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    _populate_sdl2_cache(working_dir)
    for java_file in (_sdl2_cache_root(working_dir) / "java").iterdir():
        if java_file.suffix == ".java":
            shutil.copy2(java_file, dest_dir / java_file.name)
    print(f"[ksproject] SDL2 Java source installed to {dest_dir}")


def _install_sdl2_headers(main_dir: Path, working_dir: Path) -> None:
    """Copy SDL2 C headers into src/main/cpp/sdl2_include/ for the NDK build."""
    dest_dir = main_dir / "cpp" / "sdl2_include"
    if dest_dir.exists() and any(dest_dir.iterdir()):
        return
    _populate_sdl2_cache(working_dir)
    src = _sdl2_cache_root(working_dir) / "include"
    shutil.copytree(src, dest_dir)
    print(f"[ksproject] SDL2 headers installed to {dest_dir}")


def _copy_pure_python(src: Path, dst: Path) -> None:
    _SKIP_DIRS = {"lib-dynload", "test", "tests", "__pycache__", "site-packages"}
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.is_dir():
            if child.name in _SKIP_DIRS:
                continue
            _copy_pure_python(child, dst / child.name)
        elif child.suffix not in {".so", ".pyc"}:
            shutil.copy2(child, dst / child.name)

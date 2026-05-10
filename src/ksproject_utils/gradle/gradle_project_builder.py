"""Orchestrates Gradle project generation. Ported from GradleProjectBuilder.swift."""
from __future__ import annotations

import shutil
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
    # Generation
    # ------------------------------------------------------------------

    def generate(self) -> None:
        dist_dir = self.working_dir / "project_dist" / "gradle"
        dist_dir.mkdir(parents=True, exist_ok=True)

        # Resolve toolchain first — we need the SDK path for local.properties
        toolchain = AndroidToolchain.resolve(self.android, self.working_dir)

        # Root Gradle files
        GradleBuildFiles.write_root_build_gradle(dist_dir)
        GradleBuildFiles.write_settings_gradle(dist_dir, self.app_name)
        GradleBuildFiles.write_gradle_properties(dist_dir)
        GradleBuildFiles.write_gradle_wrapper(dist_dir, toolchain.java_path)
        GradleBuildFiles.write_local_properties(dist_dir, toolchain.sdk_path)

        # app module
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
        )

        main_dir = app_dir / "src" / "main"
        main_dir.mkdir(parents=True, exist_ok=True)
        GradleBuildFiles.write_android_manifest(
            main_dir,
            package_name=self.package_name,
            app_name=self.app_name,
        )

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
                dst_lib = jni_abi / f"libpython{PY_VERSION}.so"
                if not dst_lib.exists():
                    shutil.copy2(src_lib, dst_lib)
                # SDLActivity getLibraries() loads "python3" → libpython3.so
                dst_lib_short = jni_abi / "libpython3.so"
                if not dst_lib_short.exists():
                    shutil.copy2(src_lib, dst_lib_short)

            lib_dynload = prefix / f"lib/python{PY_VERSION}/lib-dynload"
            if lib_dynload.exists():
                for so_file in lib_dynload.iterdir():
                    if so_file.suffix == ".so":
                        dst = jni_abi / so_file.name
                        if not dst.exists():
                            shutil.copy2(so_file, dst)

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


def _copy_pure_python(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.is_dir():
            if child.name == "lib-dynload":
                continue
            _copy_pure_python(child, dst / child.name)
        elif child.suffix != ".so":
            shutil.copy2(child, dst / child.name)

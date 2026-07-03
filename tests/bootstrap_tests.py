from ksp_bootstraps.bootstrap import BootstrapProtocol
from ksp_bootstraps.pyproject_models.pyproject_toml import KivySchoolProtocol, AndroidProtocol, IosProtocol, MacOSProtocol, AppleProtocol
from ksproject_utils.pyproject_toml import PyProjectToml

from ksp_bootstraps.bootstraps.kivy import KivyBootstrap

from ksp_bootstraps.platforms import Platform

from pathlib import Path

class ProjectTest():

    def install_cpython(self):
        raise NotImplementedError()

    def android_prefix(self, ks_root: Path, arch: str, android_version: str) -> Path:
        raise NotImplementedError()

    @property
    def android_default_api_version(self) -> int:
        raise NotImplementedError()
    
    @property
    def android_sdk_path(self) -> str: ...
    
    @property
    def android_ndk_version(self) -> str: ...
    
    @property
    def android_ndk_path(self) -> str: ...
    
    @property
    def android_java_path(self) -> str: ...
    
    @property
    def android_py_version(self) -> str: ...

    @property
    def py_version(self) -> str:
        raise NotImplementedError()
    
    @property
    def working_dir(self) -> Path: ...



py_project = PyProjectToml("")
_ks_data = py_project.tool.kivy_school
if _ks_data: 
    and_data = _ks_data.android
    if and_data:
        android_data: AndroidProtocol = and_data
    
    _apple_data = _ks_data.apple
    if _apple_data is None: raise Exception()
    if _apple_data:
        apple_data: AppleProtocol = _apple_data
    _ios_data = _apple_data.ios
    if _ios_data:
        ios_data: IosProtocol = _ios_data
    _macos_data = _apple_data.macos
    if _macos_data:
        macos_data: MacOSProtocol = _macos_data

    ks_data: KivySchoolProtocol = _ks_data

bootstrap: BootstrapProtocol = KivyBootstrap(py_project, ProjectTest())
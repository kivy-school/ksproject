import os
import toml

from kivy.properties import AliasProperty, ObjectProperty
from kivy.event import EventDispatcher
from ksproject_utils.pyproject_toml import KivySchoolData


class PyProjectData(EventDispatcher):
    """
    Fully flattened EventDispatcher wrapper for KivySchoolData.
    Exposes all nested platform data as Kivy properties for direct UI binding.
    """

    data = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        print(self.data)

    def on_data(self, *args) -> None:
        print(self.data.app_name)

    # =========================================================================
    # TOP-LEVEL PROPERTIES
    # =========================================================================
    def _get_app_name(self):
        return self.data.app_name if self.data else None

    def _set_app_name(self, value):
        if self.data:
            self.data.app_name = value
            return True
        return False

    app_name = AliasProperty(_get_app_name, _set_app_name, bind=["data"])

    # =========================================================================
    # IOS PROPERTIES
    # =========================================================================
    def _get_ios_bundle_id(self):
        return self.data.ios.bundle_id if self.data and self.data.ios else ""

    def _set_ios_bundle_id(self, value):
        if self.data and self.data.ios:
            self.data.ios.bundle_id = value
            return True
        return False

    ios_bundle_id = AliasProperty(_get_ios_bundle_id, _set_ios_bundle_id, bind=["data"])

    def _get_ios_info_plist(self):
        return self.data.ios.info_plist if self.data and self.data.ios else {}

    def _set_ios_info_plist(self, value):
        if self.data and self.data.ios:
            self.data.ios.info_plist = value
            return True
        return False

    ios_info_plist = AliasProperty(
        _get_ios_info_plist, _set_ios_info_plist, bind=["data"]
    )

    def _get_ios_entitlements(self):
        return self.data.ios.entitlements if self.data and self.data.ios else {}

    def _set_ios_entitlements(self, value):
        if self.data and self.data.ios:
            self.data.ios.entitlements = value
            return True
        return False

    ios_entitlements = AliasProperty(
        _get_ios_entitlements, _set_ios_entitlements, bind=["data"]
    )

    def _get_ios_permissions(self):
        return self.data.ios.permissions if self.data and self.data.ios else []

    def _set_ios_permissions(self, value):
        if self.data and self.data.ios:
            self.data.ios.permissions = value
            return True
        return False

    ios_permissions = AliasProperty(
        _get_ios_permissions, _set_ios_permissions, bind=["data"]
    )

    def _get_ios_frameworks(self):
        return self.data.ios.frameworks if self.data and self.data.ios else []

    def _set_ios_frameworks(self, value):
        if self.data and self.data.ios:
            self.data.ios.frameworks = value
            return True
        return False

    ios_frameworks = AliasProperty(
        _get_ios_frameworks, _set_ios_frameworks, bind=["data"]
    )

    def _get_ios_site_frameworks(self):
        return self.data.ios.site_frameworks if self.data and self.data.ios else []

    def _set_ios_site_frameworks(self, value):
        if self.data and self.data.ios:
            self.data.ios.site_frameworks = value
            return True
        return False

    ios_site_frameworks = AliasProperty(
        _get_ios_site_frameworks, _set_ios_site_frameworks, bind=["data"]
    )

    def _get_ios_developer_team(self):
        return self.data.ios.developer_team if self.data and self.data.ios else None

    def _set_ios_developer_team(self, value):
        if self.data and self.data.ios:
            self.data.ios.developer_team = value
            return True
        return False

    ios_developer_team = AliasProperty(
        _get_ios_developer_team, _set_ios_developer_team, bind=["data"]
    )

    # =========================================================================
    # MACOS PROPERTIES
    # =========================================================================
    def _get_macos_bundle_id(self):
        return self.data.macos.bundle_id if self.data and self.data.macos else ""

    def _set_macos_bundle_id(self, value):
        if self.data and self.data.macos:
            self.data.macos.bundle_id = value
            return True
        return False

    macos_bundle_id = AliasProperty(
        _get_macos_bundle_id, _set_macos_bundle_id, bind=["data"]
    )

    def _get_macos_info_plist(self):
        return self.data.macos.info_plist if self.data and self.data.macos else {}

    def _set_macos_info_plist(self, value):
        if self.data and self.data.macos:
            self.data.macos.info_plist = value
            return True
        return False

    macos_info_plist = AliasProperty(
        _get_macos_info_plist, _set_macos_info_plist, bind=["data"]
    )

    def _get_macos_entitlements(self):
        return self.data.macos.entitlements if self.data and self.data.macos else {}

    def _set_macos_entitlements(self, value):
        if self.data and self.data.macos:
            self.data.macos.entitlements = value
            return True
        return False

    macos_entitlements = AliasProperty(
        _get_macos_entitlements, _set_macos_entitlements, bind=["data"]
    )

    def _get_macos_developer_team(self):
        return self.data.macos.developer_team if self.data and self.data.macos else None

    def _set_macos_developer_team(self, value):
        if self.data and self.data.macos:
            self.data.macos.developer_team = value
            return True
        return False

    macos_developer_team = AliasProperty(
        _get_macos_developer_team, _set_macos_developer_team, bind=["data"]
    )

    # =========================================================================
    # ANDROID PROPERTIES
    # =========================================================================
    def _get_android_package_name(self):
        return self.data.android.package_name if self.data and self.data.android else ""

    def _set_android_package_name(self, value):
        if self.data and self.data.android:
            self.data.android.package_name = value
            return True
        return False

    android_package_name = AliasProperty(
        _get_android_package_name, _set_android_package_name, bind=["data"]
    )

    def _get_android_archs(self):
        return self.data.android.archs if self.data and self.data.android else []

    def _set_android_archs(self, value):
        if self.data and self.data.android:
            self.data.android.archs = value
            return True
        return False

    android_archs = AliasProperty(_get_android_archs, _set_android_archs, bind=["data"])

    def _get_android_api(self):
        return self.data.android.api if self.data and self.data.android else None

    def _set_android_api(self, value):
        if self.data and self.data.android:
            self.data.android.api = value
            return True
        return False

    android_api = AliasProperty(_get_android_api, _set_android_api, bind=["data"])

    def _get_android_min_api(self):
        return self.data.android.min_api if self.data and self.data.android else None

    def _set_android_min_api(self, value):
        if self.data and self.data.android:
            self.data.android.min_api = value
            return True
        return False

    android_min_api = AliasProperty(
        _get_android_min_api, _set_android_min_api, bind=["data"]
    )

    def _get_android_sdk(self):
        return self.data.android.sdk if self.data and self.data.android else None

    def _set_android_sdk(self, value):
        if self.data and self.data.android:
            self.data.android.sdk = value
            return True
        return False

    android_sdk = AliasProperty(_get_android_sdk, _set_android_sdk, bind=["data"])

    def _get_android_ndk(self):
        return self.data.android.ndk if self.data and self.data.android else None

    def _set_android_ndk(self, value):
        if self.data and self.data.android:
            self.data.android.ndk = value
            return True
        return False

    android_ndk = AliasProperty(_get_android_ndk, _set_android_ndk, bind=["data"])

    def _get_android_ndk_api(self):
        return self.data.android.ndk_api if self.data and self.data.android else None

    def _set_android_ndk_api(self, value):
        if self.data and self.data.android:
            self.data.android.ndk_api = value
            return True
        return False

    android_ndk_api = AliasProperty(
        _get_android_ndk_api, _set_android_ndk_api, bind=["data"]
    )

    def _get_android_sdk_path(self):
        return self.data.android.sdk_path if self.data and self.data.android else None

    def _set_android_sdk_path(self, value):
        if self.data and self.data.android:
            self.data.android.sdk_path = value
            return True
        return False

    android_sdk_path = AliasProperty(
        _get_android_sdk_path, _set_android_sdk_path, bind=["data"]
    )

    def _get_android_ndk_path(self):
        return self.data.android.ndk_path if self.data and self.data.android else None

    def _set_android_ndk_path(self, value):
        if self.data and self.data.android:
            self.data.android.ndk_path = value
            return True
        return False

    android_ndk_path = AliasProperty(
        _get_android_ndk_path, _set_android_ndk_path, bind=["data"]
    )

    def _get_android_java_path(self):
        return self.data.android.java_path if self.data and self.data.android else None

    def _set_android_java_path(self, value):
        if self.data and self.data.android:
            self.data.android.java_path = value
            return True
        return False

    android_java_path = AliasProperty(
        _get_android_java_path, _set_android_java_path, bind=["data"]
    )

    def _get_android_global_tools(self):
        return (
            self.data.android.global_tools if self.data and self.data.android else False
        )

    def _set_android_global_tools(self, value):
        if self.data and self.data.android:
            self.data.android.global_tools = bool(value)
            return True
        return False

    android_global_tools = AliasProperty(
        _get_android_global_tools, _set_android_global_tools, bind=["data"]
    )

    def _get_android_global_tools_path(self):
        return (
            self.data.android.global_tools_path
            if self.data and self.data.android
            else None
        )

    def _set_android_global_tools_path(self, value):
        if self.data and self.data.android:
            self.data.android.global_tools_path = value
            return True
        return False

    android_global_tools_path = AliasProperty(
        _get_android_global_tools_path, _set_android_global_tools_path, bind=["data"]
    )

    def _get_android_icon(self):
        return self.data.android.icon if self.data and self.data.android else None

    def _set_android_icon(self, value):
        if self.data and self.data.android:
            self.data.android.icon = value
            return True
        return False

    android_icon = AliasProperty(_get_android_icon, _set_android_icon, bind=["data"])

    def _get_android_presplash(self):
        return self.data.android.presplash if self.data and self.data.android else None

    def _set_android_presplash(self, value):
        if self.data and self.data.android:
            self.data.android.presplash = value
            return True
        return False

    android_presplash = AliasProperty(
        _get_android_presplash, _set_android_presplash, bind=["data"]
    )

    def _get_android_presplash_color(self):
        return (
            self.data.android.presplash_color
            if self.data and self.data.android
            else None
        )

    def _set_android_presplash_color(self, value):
        if self.data and self.data.android:
            self.data.android.presplash_color = value
            return True
        return False

    android_presplash_color = AliasProperty(
        _get_android_presplash_color, _set_android_presplash_color, bind=["data"]
    )

    def _get_android_presplash_lottie(self):
        return (
            self.data.android.presplash_lottie
            if self.data and self.data.android
            else None
        )

    def _set_android_presplash_lottie(self, value):
        if self.data and self.data.android:
            self.data.android.presplash_lottie = value
            return True
        return False

    android_presplash_lottie = AliasProperty(
        _get_android_presplash_lottie, _set_android_presplash_lottie, bind=["data"]
    )

    def _get_android_permissions(self):
        return self.data.android.permissions if self.data and self.data.android else []

    def _set_android_permissions(self, value):
        if self.data and self.data.android:
            self.data.android.permissions = value
            return True
        return False

    android_permissions = AliasProperty(
        _get_android_permissions, _set_android_permissions, bind=["data"]
    )

    def _get_android_meta_data(self):
        return self.data.android.meta_data if self.data and self.data.android else {}

    def _set_android_meta_data(self, value):
        if self.data and self.data.android:
            self.data.android.meta_data = value
            return True
        return False

    android_meta_data = AliasProperty(
        _get_android_meta_data, _set_android_meta_data, bind=["data"]
    )

    def _get_android_gradle_dependencies(self):
        return (
            self.data.android.gradle_dependencies
            if self.data and self.data.android
            else []
        )

    def _set_android_gradle_dependencies(self, value):
        if self.data and self.data.android:
            self.data.android.gradle_dependencies = value
            return True
        return False

    android_gradle_dependencies = AliasProperty(
        _get_android_gradle_dependencies,
        _set_android_gradle_dependencies,
        bind=["data"],
    )

    def _get_android_services(self):
        return self.data.android.services if self.data and self.data.android else []

    def _set_android_services(self, value):
        if self.data and self.data.android:
            self.data.android.services = value
            return True
        return False

    android_services = AliasProperty(
        _get_android_services, _set_android_services, bind=["data"]
    )

toml_path = os.path.join(os.getcwd(), "pyproject.toml")
with open(toml_path, "r") as f:
    full_toml_dict = toml.load(f)

kivy_school_dict = full_toml_dict.get("tool", {}).get("kivy-school", {})

kivyschool_data = KivySchoolData(data=kivy_school_dict)
datamodel = PyProjectData()

datamodel.data = kivyschool_data

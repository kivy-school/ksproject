"""Build a single XcodeGen target dict.

Ports ``PSProject/Sources/XcodeProjectBuilder/ProjectTarget/*.swift``
(including ``BuildScripts.swift``) for the single supported "kivy" stack
(SDL2 + KivyLauncher + PySwiftKit + CPython).
"""
from __future__ import annotations

from typing import Any

from . import setting_presets as sp
from .plist_templates import IOS_PROJECT_PLIST_KEYS


PY_SUB_VERSION = 13


# --------------------------------------------------------------------------
# Build script bodies (ported verbatim from BuildScripts.swift)
# --------------------------------------------------------------------------

INSTALL_APP_MODULE_SCRIPT = r"""export PATH="$HOME/.local/bin:$PATH"

APP_SRC="$PROJECT_DIR/../../"
PIP3="uv pip"
PIP_ARGS="--compile -U --no-deps"

if [ "$EFFECTIVE_PLATFORM_NAME" = "-iphonesimulator" ]; then
    echo "Installing App module for iOS Simulator"
    $PIP3 install $APP_SRC $PIP_ARGS -t "$PROJECT_DIR/site_packages/iphonesimulator/"
elif [ "$EFFECTIVE_PLATFORM_NAME" = "-iphoneos" ]; then
    echo "Installing App module for iOS"
    $PIP3 install $APP_SRC $PIP_ARGS -t "$PROJECT_DIR/site_packages/iphoneos/"
else
    echo "Installing App module for macOS"
    $PIP3 install $APP_SRC $PIP_ARGS -t "$PROJECT_DIR/site_packages/macos/"
fi
"""


_INSTALL_PY_IOS = r"""mkdir -p "$CODESIGNING_FOLDER_PATH/python/lib"
if [ "$EFFECTIVE_PLATFORM_NAME" = "-iphonesimulator" ]; then
    echo "Installing Python modules for iOS Simulator"
    SIM_ARCH=$(uname -m)
    rsync -au --delete "$PROJECT_DIR/Frameworks/Python.xcframework/lib/python3.13/" "$CODESIGNING_FOLDER_PATH/python/lib/"
    rsync -au --delete "$PROJECT_DIR/Frameworks/Python.xcframework/ios-arm64_x86_64-simulator/lib-${SIM_ARCH}/python3.13/lib-dynload" "$CODESIGNING_FOLDER_PATH/python/lib/"
    rsync -au --delete "$PROJECT_DIR/site_packages/iphonesimulator/" "$CODESIGNING_FOLDER_PATH/python/site_packages"
else
    echo "Installing Python modules for iOS Device"
    rsync -au --delete "$PROJECT_DIR/Frameworks/Python.xcframework/lib/python3.13/" "$CODESIGNING_FOLDER_PATH/python/lib"
    rsync -au --delete "$PROJECT_DIR/Frameworks/Python.xcframework/ios-arm64/lib-arm64/python3.13/lib-dynload" "$CODESIGNING_FOLDER_PATH/python/lib/"
    rsync -au --delete "$PROJECT_DIR/site_packages/iphoneos/" "$CODESIGNING_FOLDER_PATH/python/site_packages"
fi
rm -rf "$CODESIGNING_FOLDER_PATH/python/site_packages/bin"
rm -rf "$CODESIGNING_FOLDER_PATH/python/site_packages/.java"
rm "$CODESIGNING_FOLDER_PATH/python/site_packages/.lock"
#rsync -au --delete "$PROJECT_DIR/app/" "$CODESIGNING_FOLDER_PATH/app"
"""


_INSTALL_PY_MACOS = r"""rsync -au --delete "$PROJECT_DIR/Frameworks/macos-arm64_x86_64/lib/" "$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/python/lib"

SITE_DST="$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/site_packages"
mkdir -p $SITE_DST
mkdir -p "$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/app"
echo "Installing Python modules for macOS Device"
rsync -au --delete "$PROJECT_DIR/site_packages/macos/" $SITE_DST
rsync -au --delete "$PROJECT_DIR/app/" "$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/app"
"""


def _indent(s: str, prefix: str) -> str:
    return s.replace("\n", "\n" + prefix)


INSTALL_PY_MODULES_SCRIPT = f"""set -e
if [ "$EFFECTIVE_PLATFORM_NAME" = "-iphonesimulator" ] || [ "$EFFECTIVE_PLATFORM_NAME" = "-iphoneos" ]; then
    echo "Installing Python modules for iOS Device/Simulator"
    {_indent(_INSTALL_PY_IOS, "    ")}
else
    echo "Installing Python modules for macOS"
    {_indent(_INSTALL_PY_MACOS, "    ")}
fi

PYTHON="$PROJECT_DIR/python3"
PY_APP="$CODESIGNING_FOLDER_PATH/app"
PY_SITE="$CODESIGNING_FOLDER_PATH/site_packages"
"""


_SIGN_PY_IOS_BODY = r"""install_dylib () {
    INSTALL_BASE=$1
    FULL_EXT=$2

    EXT=$(basename "$FULL_EXT")
    RELATIVE_EXT=${FULL_EXT#$CODESIGNING_FOLDER_PATH/}
    PYTHON_EXT=${RELATIVE_EXT/$INSTALL_BASE/}
    FULL_MODULE_NAME=$(echo $PYTHON_EXT | cut -d "." -f 1 | tr "/" ".");
    FRAMEWORK_BUNDLE_ID=$(echo $PRODUCT_BUNDLE_IDENTIFIER.$FULL_MODULE_NAME | tr "_" "-")
    FRAMEWORK_FOLDER="Frameworks/$FULL_MODULE_NAME.framework"

    if [ ! -d "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER" ]; then
        echo "Creating framework for $RELATIVE_EXT"
        mkdir -p "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER"

        cp "$CODESIGNING_FOLDER_PATH/dylib-Info-template.plist" "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/Info.plist"
        plutil -replace CFBundleExecutable -string "$FULL_MODULE_NAME" "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/Info.plist"
        plutil -replace CFBundleIdentifier -string "$FRAMEWORK_BUNDLE_ID" "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/Info.plist"
    fi

    echo "Installing binary for $FRAMEWORK_FOLDER/$FULL_MODULE_NAME"
    mv "$FULL_EXT" "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/$FULL_MODULE_NAME"

    echo "$FRAMEWORK_FOLDER/$FULL_MODULE_NAME" > ${FULL_EXT%.so}.fwork
    echo "${RELATIVE_EXT%.so}.fwork" > "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/$FULL_MODULE_NAME.origin"

    XCPRIVACY_FILE="$(dirname "$FULL_EXT")/$(echo $EXT | cut -d '.' -f 1).xcprivacy"
    if [ -f "$XCPRIVACY_FILE" ]; then
        echo "Copying privacy manifest for $FULL_MODULE_NAME"
        cp "$XCPRIVACY_FILE" "$CODESIGNING_FOLDER_PATH/$FRAMEWORK_FOLDER/PrivacyInfo.xcprivacy"
    fi
}

echo "Install standard library extension modules..."
find "$CODESIGNING_FOLDER_PATH/python/lib/python3.__SUBVER__/lib-dynload" -name "*.so" | while read FULL_EXT; do
    install_dylib python/lib/python3.__SUBVER__/lib-dynload/ "$FULL_EXT"
done
echo "Install app package extension modules..."
find "$CODESIGNING_FOLDER_PATH/site_packages" -name "*.so" | while read FULL_EXT; do
    install_dylib app_packages/ "$FULL_EXT"
done
echo "Install app extension modules..."
find "$CODESIGNING_FOLDER_PATH/app" -name "*.so" | while read FULL_EXT; do
    install_dylib app/ "$FULL_EXT"
done

rm -f "$CODESIGNING_FOLDER_PATH/dylib-Info-template.plist"

echo "Signing frameworks as $EXPANDED_CODE_SIGN_IDENTITY_NAME ($EXPANDED_CODE_SIGN_IDENTITY)..."
find "$CODESIGNING_FOLDER_PATH/Frameworks" -name "*.framework" -exec /usr/bin/codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY" ${OTHER_CODE_SIGN_FLAGS:-} -o runtime --timestamp=none --preserve-metadata=identifier,entitlements,flags --generate-entitlement-der "{}" \;
"""


_SIGN_PY_MACOS_BODY = r"""echo "Signed as $EXPANDED_CODE_SIGN_IDENTITY_NAME ($EXPANDED_CODE_SIGN_IDENTITY)"

find "$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/site_packages" -name "*.so" -exec /usr/bin/codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY" -o runtime --timestamp=none --preserve-metadata=identifier,entitlements,flags --generate-entitlement-der {} \;
find "$BUILT_PRODUCTS_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH/app" -name "*.so" -exec /usr/bin/codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY" -o runtime --timestamp=none --preserve-metadata=identifier,entitlements,flags --generate-entitlement-der {} \;
"""


def _sign_python_binary_script(sub_version: int) -> str:
    ios_body = _SIGN_PY_IOS_BODY.replace("__SUBVER__", str(sub_version))
    return f"""set -e
if [ "$EFFECTIVE_PLATFORM_NAME" = "-iphonesimulator" ] || [ "$EFFECTIVE_PLATFORM_NAME" = "-iphoneos" ]; then
    echo "Installing Python modules for iOS Device/Simulator"
    {_indent(ios_body, "    ")}
else
    echo "Installing Python modules for macOS"
    {_indent(_SIGN_PY_MACOS_BODY, "    ")}
fi
"""


SIGN_PYTHON_BINARY_SCRIPT = _sign_python_binary_script(PY_SUB_VERSION)


# --------------------------------------------------------------------------
# Target builder
# --------------------------------------------------------------------------

class ProjectTarget:
    """One XcodeGen target (single multi-platform "auto" application target)."""

    def __init__(
        self,
        name: str,
        info_plist_extra: dict[str, Any],
        entitlements: dict[str, Any] | None,
        site_xcframeworks: list[str] | None = None,
        developer_team: str | None = None,
    ) -> None:
        self.name = name
        self.info_plist_extra = info_plist_extra
        self.entitlements = entitlements
        self.site_xcframeworks: list[str] = site_xcframeworks or []
        self.developer_team = developer_team

    # ----- settings -----

    def _settings(self) -> dict[str, Any]:
        base: dict[str, Any] = {
            "LIBRARY_SEARCH_PATHS": ["$(inherited)"],
            "LD_RUNPATH_SEARCH_PATHS": [
                "$(inherited)",
                "@executable_path/Frameworks",
                "@executable_path/../Frameworks",
            ],
            "ENABLE_BITCODE": False,
            "CODE_SIGN_STYLE": "Automatic",
        }
        if self.developer_team:
            base["DEVELOPMENT_TEAM"] = self.developer_team
        merged = sp.merged(
            sp.target_settings("auto"),
            sp.supported_destination_settings(["iOS", "macOS"]),
            base,
        )
        return {
            "configs": {
                "Debug": merged,
                "Release": merged,
            }
        }

    # ----- sources -----

    def _sources(self) -> list[dict[str, Any]]:
        return [
            {"path": "Resources/Images.xcassets", "group": "Resources"},
            {
                "path": "Sources/IphoneOS",
                "group": "Sources",
                "type": "group",
                "destinationFilters": ["iOS"],
            },
            {
                "path": "Sources/MacOS",
                "group": "Sources",
                "type": "group",
                "destinationFilters": ["macOS"],
            },
            {"path": "Sources/Shared", "group": "Sources", "type": "group"},
            {
                "path": "Resources/Launch Screen.storyboard",
                "group": "Resources",
                "destinationFilters": ["iOS"],
            },
            {"path": "Frameworks/dylib-Info-template.plist", "group": "Support"},
        ]

    # ----- dependencies -----

    def _dependencies(self) -> list[dict[str, Any]]:
        deps: list[dict[str, Any]] = [
            # {"package": "PySwiftKit", "product": "PySwiftKitBase"},
            # {"package": "CPython", "product": "CPython"},
            # {"package": "KivyLauncher", "product": "KivyLauncher"},
            # {
            #     "package": "Kivy_iOS_Module",
            #     "product": "Kivy_iOS_Module",
            #     "platformFilter": "iOS",
            # },
            {"package": "PathKit", "product": "PathKit"},
            {"framework": "Frameworks/Python.xcframework"}
        ]
        for fw_name in self.site_xcframeworks:
            if fw_name == "Python.xcframework": continue
            deps.append({"framework": f"Frameworks/{fw_name}", "platformFilter": "iOS"})
        return deps

    # ----- info / entitlements -----

    def _info(self) -> dict[str, Any]:
        keys = dict(IOS_PROJECT_PLIST_KEYS)
        keys.update(self.info_plist_extra)
        return {"path": "Sources/Info.plist", "properties": keys}

    def _entitlements(self) -> dict[str, Any] | None:
        if not self.entitlements:
            return None
        return {
            "path": f"{self.name}.entitlements",
            "properties": dict(self.entitlements),
        }

    # ----- scripts -----

    def _post_build_scripts(self) -> list[dict[str, Any]]:
        return [
            {"script": INSTALL_APP_MODULE_SCRIPT, "name": "Install App Module"},
            {
                "script": INSTALL_PY_MODULES_SCRIPT,
                "name": "Install target specific Python modules",
            },
            {"script": SIGN_PYTHON_BINARY_SCRIPT, "name": "Sign Python Binary Modules"},
        ]

    # ----- export -----

    def to_dict(self) -> dict[str, Any]:
        target: dict[str, Any] = {
            "type": "application",
            "platform": "auto",
            "supportedDestinations": ["iOS", "macOS"],
            "settings": self._settings(),
            "sources": self._sources(),
            "dependencies": self._dependencies(),
            "info": self._info(),
            "requiresObjCLinking": True,
            "postBuildScripts": self._post_build_scripts(),
        }
        ent = self._entitlements()
        if ent is not None:
            target["entitlements"] = ent
        return target

"""XcodeGen SettingPresets ported to Python.

Mirrors ``PSProject/Sources/XcodeProjectBuilder/SettingPresets.swift`` which
itself reproduces XcodeGen's bundled ``SettingPresets/*.yml`` dictionaries.
"""

from __future__ import annotations

from typing import Any

BuildSettings = dict[str, Any]


BASE: BuildSettings = {
    "ALWAYS_SEARCH_USER_PATHS": "NO",
    "CLANG_ANALYZER_NONNULL": "YES",
    "CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION": "YES_AGGRESSIVE",
    "CLANG_CXX_LANGUAGE_STANDARD": "gnu++14",
    "CLANG_CXX_LIBRARY": "libc++",
    "CLANG_ENABLE_MODULES": "YES",
    "CLANG_ENABLE_OBJC_ARC": "YES",
    "CLANG_ENABLE_OBJC_WEAK": "YES",
    "CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING": "YES",
    "CLANG_WARN_BOOL_CONVERSION": "YES",
    "CLANG_WARN_COMMA": "YES",
    "CLANG_WARN_CONSTANT_CONVERSION": "YES",
    "CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS": "YES",
    "CLANG_WARN_DIRECT_OBJC_ISA_USAGE": "YES_ERROR",
    "CLANG_WARN_DOCUMENTATION_COMMENTS": "YES",
    "CLANG_WARN_EMPTY_BODY": "YES",
    "CLANG_WARN_ENUM_CONVERSION": "YES",
    "CLANG_WARN_INFINITE_RECURSION": "YES",
    "CLANG_WARN_INT_CONVERSION": "YES",
    "CLANG_WARN_NON_LITERAL_NULL_CONVERSION": "YES",
    "CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF": "YES",
    "CLANG_WARN_OBJC_LITERAL_CONVERSION": "YES",
    "CLANG_WARN_OBJC_ROOT_CLASS": "YES_ERROR",
    "CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER": "YES",
    "CLANG_WARN_RANGE_LOOP_ANALYSIS": "YES",
    "CLANG_WARN_STRICT_PROTOTYPES": "YES",
    "CLANG_WARN_SUSPICIOUS_MOVE": "YES",
    "CLANG_WARN_UNGUARDED_AVAILABILITY": "YES_AGGRESSIVE",
    "CLANG_WARN_UNREACHABLE_CODE": "YES",
    "CLANG_WARN__DUPLICATE_METHOD_MATCH": "YES",
    "COPY_PHASE_STRIP": "NO",
    "ENABLE_STRICT_OBJC_MSGSEND": "YES",
    "GCC_C_LANGUAGE_STANDARD": "gnu11",
    "GCC_NO_COMMON_BLOCKS": "YES",
    "GCC_WARN_64_TO_32_BIT_CONVERSION": "YES",
    "GCC_WARN_ABOUT_RETURN_TYPE": "YES_ERROR",
    "GCC_WARN_UNDECLARED_SELECTOR": "YES",
    "GCC_WARN_UNINITIALIZED_AUTOS": "YES_AGGRESSIVE",
    "GCC_WARN_UNUSED_FUNCTION": "YES",
    "GCC_WARN_UNUSED_VARIABLE": "YES",
    "MTL_FAST_MATH": "YES",
    "PRODUCT_NAME": "$(TARGET_NAME)",
    "SWIFT_VERSION": "5.0",
}


CONFIG_DEBUG: BuildSettings = {
    "DEBUG_INFORMATION_FORMAT": "dwarf",
    "ENABLE_TESTABILITY": "YES",
    "GCC_DYNAMIC_NO_PIC": "NO",
    "GCC_OPTIMIZATION_LEVEL": "0",
    "GCC_PREPROCESSOR_DEFINITIONS": ["$(inherited)", "DEBUG=1"],
    "MTL_ENABLE_DEBUG_INFO": "INCLUDE_SOURCE",
    "ONLY_ACTIVE_ARCH": "YES",
    "SWIFT_ACTIVE_COMPILATION_CONDITIONS": "DEBUG",
    "SWIFT_OPTIMIZATION_LEVEL": "-Onone",
}


CONFIG_RELEASE: BuildSettings = {
    "DEBUG_INFORMATION_FORMAT": "dwarf-with-dsym",
    "ENABLE_NS_ASSERTIONS": "NO",
    "MTL_ENABLE_DEBUG_INFO": "NO",
    "SWIFT_COMPILATION_MODE": "wholemodule",
    "SWIFT_OPTIMIZATION_LEVEL": "-O",
}


PLATFORM_IOS: BuildSettings = {
    "LD_RUNPATH_SEARCH_PATHS": ["$(inherited)", "@executable_path/Frameworks"],
    "SDKROOT": "iphoneos",
    "TARGETED_DEVICE_FAMILY": "1,2",
}

PLATFORM_MACOS: BuildSettings = {
    "LD_RUNPATH_SEARCH_PATHS": ["$(inherited)", "@executable_path/../Frameworks"],
    "SDKROOT": "macosx",
    "COMBINE_HIDPI_IMAGES": "YES",
}


SUPPORTED_DESTINATION_IOS: BuildSettings = {
    "SUPPORTED_PLATFORMS": "iphoneos iphonesimulator",
    "TARGETED_DEVICE_FAMILY": "1,2",
    "SUPPORTS_MACCATALYST": "NO",
    "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD": "YES",
    "SUPPORTS_XR_DESIGNED_FOR_IPHONE_IPAD": "YES",
}


SUPPORTED_DESTINATION_MACOS: BuildSettings = {
    "SUPPORTED_PLATFORMS": "macosx",
    "SUPPORTS_MACCATALYST": "NO",
    "SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD": "NO",
}


PRODUCT_APPLICATION: BuildSettings = {}


PRODUCT_PLATFORM_APPLICATION_IOS: BuildSettings = {
    "CODE_SIGN_IDENTITY": "iPhone Developer",
    "ASSETCATALOG_COMPILER_APPICON_NAME": "AppIcon",
}


PRODUCT_PLATFORM_APPLICATION_MACOS: BuildSettings = {
    "ASSETCATALOG_COMPILER_APPICON_NAME": "AppIcon",
}


def merged(*dicts: BuildSettings) -> BuildSettings:
    """Shallow-merge multiple dicts in order (later wins)."""
    result: BuildSettings = {}
    for d in dicts:
        result.update(d)
    return result


def project_settings(config_type: str) -> BuildSettings:
    """Project-level preset settings for a given config (``debug``/``release``)."""
    if config_type == "debug":
        return merged(BASE, CONFIG_DEBUG)
    if config_type == "release":
        return merged(BASE, CONFIG_RELEASE)
    raise ValueError(f"Unknown config_type: {config_type!r}")


def _platform_settings(platform: str) -> BuildSettings:
    if platform == "iOS":
        return PLATFORM_IOS
    if platform == "macOS":
        return PLATFORM_MACOS
    if platform == "auto":
        return {}
    raise ValueError(f"Unknown platform: {platform!r}")


def target_settings(platform: str = "auto") -> BuildSettings:
    """Target-level preset settings for a given platform (application product)."""
    return merged(_platform_settings(platform), PRODUCT_APPLICATION)


def supported_destination_settings(destinations: list[str]) -> BuildSettings:
    """Reproduce XcodeGen's per-destination merge.

    ``SUPPORTED_PLATFORMS`` and ``TARGETED_DEVICE_FAMILY`` get concatenated.
    """
    by_dest = {
        "iOS": SUPPORTED_DESTINATION_IOS,
        "macOS": SUPPORTED_DESTINATION_MACOS,
    }
    # PSProject's sort order: iOS before macOS (lower .priority).
    priorities = {"iOS": 0, "macOS": 1}
    sorted_dests = sorted(destinations, key=lambda d: priorities.get(d, 99))

    result: BuildSettings = {}
    supported_platforms: list[str] = []
    targeted_device_family: list[str] = []
    for dest in sorted_dests:
        s = by_dest[dest]
        result.update(s)
        sp = s.get("SUPPORTED_PLATFORMS")
        if isinstance(sp, str):
            supported_platforms += sp.split()
        tdf = s.get("TARGETED_DEVICE_FAMILY")
        if isinstance(tdf, str):
            targeted_device_family += tdf.split(",")

    if supported_platforms:
        result["SUPPORTED_PLATFORMS"] = " ".join(supported_platforms)
    if targeted_device_family:
        result["TARGETED_DEVICE_FAMILY"] = ",".join(targeted_device_family)
    return result


def product_platform_application(platform: str) -> BuildSettings:
    if platform == "iOS":
        return PRODUCT_PLATFORM_APPLICATION_IOS
    if platform == "macOS":
        return PRODUCT_PLATFORM_APPLICATION_MACOS
    return {}

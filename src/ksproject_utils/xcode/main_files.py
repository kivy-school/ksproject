"""Per-platform ``main.swift`` template.

Bakes in the KivyLauncher backend behavior from
``PSProject/Backends/Sources/Backends/backends/KivyLauncher.swift``.
"""
from __future__ import annotations
import textwrap

def render_main_swift(platform: str) -> str:
    """Return the contents of ``main.swift`` for the given Apple platform.

    ``platform`` is ``"iOS"`` or ``"macOS"``.
    """
    imports = ""
    modules = ""

    match platform:
        case "iOS": ...
        case "macOS": ...
        case _:
            raise ValueError(f"Unsupported platform for main.swift: {platform!r}")
    
    if platform == "iOS":
        imports = "import KivyLauncher\nimport Kivy_iOS_Module"
        modules = ".ios"
    elif platform == "macOS":
        imports = "import KivyLauncher"
        modules = ""
    else:
        raise ValueError(f"Unsupported platform for main.swift: {platform!r}")
    

    return textwrap.dedent(f"""\
    import Foundation

    exit(KivyLauncher.SDLmain())
    """)

def __render_main_swift(platform: str) -> str:
    """Return the contents of ``main.swift`` for the given Apple platform.

    ``platform`` is ``"iOS"`` or ``"macOS"``.
    """
    if platform == "iOS":
        imports = "import KivyLauncher\nimport Kivy_iOS_Module"
        modules = ".ios"
    elif platform == "macOS":
        imports = "import KivyLauncher"
        modules = ""
    else:
        raise ValueError(f"Unsupported platform for main.swift: {platform!r}")

    return f"""import Foundation
import PySwiftKit
{imports}

// post_imports
KivyLauncher.pyswiftImports = [
    {modules}
]

// main
let exit_status = KivyLauncher.SDLmain()

// on_exit
exit(exit_status)
"""

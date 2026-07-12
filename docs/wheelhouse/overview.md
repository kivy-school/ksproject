# Using the Wheelhouse

Every ksproject app has a `wheelhouse/` directory at its root. It's a **local wheel repository**: any `.whl` file you drop in there becomes installable for your app — on desktop *and* inside Android/iOS/macOS builds — without publishing anything to an index.

This is the escape hatch that lets you build your own platform wheels (a patched Kivy, an unreleased dependency, a package with no mobile wheels on any index) and have ksproject pick them up like any other dependency.

---

## How It's Wired

`ksproject init` creates the `wheelhouse/` directory and configures it in your `pyproject.toml`:

```toml
[tool.uv]
index-strategy = "unsafe-best-match"
find-links = ["./wheelhouse"]

[tool.uv.pip]
extra-index-url = [
    "https://pypi-index.psychowaspx.workers.dev/simple",
    "https://pypi.anaconda.org/kivyschool/simple",
]
find-links = ["./wheelhouse"]
```

Two things matter here:

- **`find-links = ["./wheelhouse"]`** — tells uv to treat the directory as an extra source of distributions, alongside PyPI and the KivySchool indexes.
- **`index-strategy = "unsafe-best-match"`** — tells uv to consider *all* sources and pick the best candidate overall, instead of stopping at the first index that knows the package name. Without this, a package that exists on PyPI would never be picked up from your wheelhouse.

---

## When the Wheelhouse Is Consulted

The wheelhouse participates in every resolution uv performs for your project:

| Context | What happens |
|---------|--------------|
| `uv run`, `uv sync` (desktop) | Wheels matching your desktop platform are installed into `.venv` |
| `uv run ksproject android build` | ksproject runs `uv pip install --python-platform <android-arch>` per ABI; Android wheels (`*-android_*.whl`) in the wheelhouse are candidates |
| `uv run ksproject apple ios build` (or `sim` / `macos`) | Same, for iOS/macOS target platforms (`*-ios_*.whl`, `*-macosx_*.whl`) |

During a mobile build, ksproject cross-installs your project and its dependencies into per-arch `site_packages` directories. uv selects the wheel whose **platform tag** matches the target — so a single wheelhouse can hold wheels for all platforms side by side; the right one is chosen per build.

```
wheelhouse/
├── kivy-2.3.1-cp313-cp313-android_24_arm64_v8a.whl   # ← android build
├── kivy-2.3.1-cp313-cp313-ios_15_6_arm64_iphoneos.whl # ← ios build
├── kivy-2.3.1-cp313-cp313-macosx_11_0_arm64.whl       # ← macos build / desktop
└── .gitkeep
```

---

## Version Matching

A wheel in the wheelhouse is only used if its **version satisfies your dependency constraint**. Two common gotchas:

!!! warning "Pre-release versions"
    Wheels built from a development branch (e.g. Kivy master produces `3.0.0.dev0`) are **pre-releases**, and uv skips pre-releases by default. Pin the exact version to opt in:

    ```toml
    dependencies = [
        "kivy==3.0.0.dev0",
    ]
    ```

    An exact pre-release pin enables pre-release resolution for that package.

!!! tip "Same version as an index"
    If your wheelhouse wheel has the *same version* as one published on an index, `unsafe-best-match` may pick either — uv prefers the best wheel for the platform, not a specific source. To guarantee your local build wins, bump the local version (e.g. `2.3.1.post1`) and pin it.

---

## The `WHEELHOUSE` Environment Variable

When ksproject runs your `pre_build` / `post_build` scripts (configured in `[tool.kivy-school.android]` / `[tool.kivy-school.ios]`), it exports **`WHEELHOUSE`** — the absolute path to your project's wheelhouse. Use it in scripts that generate or fetch wheels as part of the build:

```python
import os
from pathlib import Path

wheelhouse = Path(os.environ["WHEELHOUSE"])
# e.g. download or build a wheel into it before site-packages install
```

---

## Filling the Wheelhouse

Any tool that produces wheels works — `uv build`, `pip wheel`, a CI artifact download. For **platform wheels targeting Android and iOS**, the recommended tool is [cibuildwheel](https://cibuildwheel.pypa.io/), which knows how to drive the Android/iOS cross-toolchains.

The next page walks through the two builds you're most likely to want:

- **[Building Kivy Wheels](building-kivy-wheels.md)** — Kivy 2.3.x (`kivy2x`) and Kivy 3.0.0 (master), for every platform ksproject targets.

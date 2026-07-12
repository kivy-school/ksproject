# Test suite for KSProject

Tiered pytest suite under `ksproject/tests/`: fast unit + hermetic integration by default, real gradle/xcode build + emulator/simulator behind markers.

- Framework: pytest (markers, fixtures, xdist)
- Layout: `tests/{unit,integration,e2e,fixtures}`
- Markers: `slow`, `android`, `apple`, `emulator`, `simulator`
- Default run: `uv run pytest -m "not slow"`

## Goals
- **G1** Catch regressions in pyproject parsing, path resolution, spec generation (fast, no I/O).
- **G2** Verify toolchain discovery (`global_tools=false` / `true` / `global_tools_path`) resolves correct SDK/NDK/framework paths.
- **G3** Verify generated Gradle/Xcode projects are structurally valid (paths exist, JNI libs / xcframeworks landed).
- **G4** Smoke-run a real app on Android emulator and iOS simulator with a Python-asserted marker.

## Phases

### Phase 1 — Scaffolding
1. Add `[dependency-groups] dev` to `ksproject/pyproject.toml` with `pytest`, `pytest-mock`, `pytest-xdist`; register markers under `[tool.pytest.ini_options]`.
2. Create `ksproject/tests/` with `conftest.py` and `unit/`, `integration/`, `e2e/`, `fixtures/`.
3. Shared fixtures in `conftest.py`: `tmp_project` (writes minimal `pyproject.toml`), `fake_kivyschool` (stubs `cmdline-tools`, `ndk`, `platforms/android-XX`, `Python.xcframework`), `skip_if_not_macos`.
4. Create `ksproject/tests/fixtures/minimal_app/` — smallest valid Kivy app.

### Phase 2 — Unit tests for `ksproject_utils`
1. **pyproject_toml** — parse, defaults, `developer_team`, `AndroidData.kivyschool_root()` three branches.
2. **pyproject_init** — round-trip: generated default toml is re-parseable by `PyProjectToml`.
3. **tools.Tools** — discovery against `fake_kivyschool`; missing-tool errors.
4. **xcode/project_target** — `DEVELOPMENT_TEAM`, `CODE_SIGN_STYLE`, `info_plist_extra`, `entitlements` merge.
5. **xcode/setting_presets** — `sp.merged()`, `target_settings("auto")`, destination shape.
6. ~~**gradle/gradle_build_files** — emitted `build.gradle` / `settings.gradle` snapshot.~~ *(removed — build-file emission moved to the `ksp_bootstraps` package (`bootstrap.generate()`); no longer in `ksproject_utils`. Covered by Phase 3 integration, not a unit snapshot here.)*

### Phase 3 — Hermetic integration
1. Android `global_tools=false` toolchain wiring → resolved paths match `<tmp>/.kivyschool/...` and default versions.
2. Android gradle project gen (no build) → `build.gradle`, `settings.gradle`, `AndroidManifest.xml`, `app/src/main/python/`; `kivy>=2.3.1` recipe present.
3. Apple `global_tools=false` framework discovery; actionable error when missing.
4. Apple xcode project gen → `.xcodeproj` exists; parse spec; `DEVELOPMENT_TEAM` injected when set; expected `.xcframework` deps.

### Phase 4 — E2E build smoke *(marker-gated)*
1. `@slow @android @emulator`: `ksproject android build --variant debug`; assert APK + `libpython*.so` / `libSDL2*.so` / `libmain.so` in `jniLibs/<abi>/`; boot AVD, install, launch, logcat marker.
2. `@slow @apple @simulator` *(macOS)*: `ksproject ios build --simulator` + `ksproject macos build`; assert `.app` + required `.xcframework`s; `simctl` launch + log marker.

### Phase 5 — CI wiring
1. `.github/workflows/tests.yml` matrix:
   - ubuntu — unit + hermetic + android hermetic
   - macos — full (incl. apple e2e; emulator opt-in)
   - windows — unit + hermetic + android hermetic
2. Cache `~/.kivyschool` per-OS.
3. Default `pytest -m "not slow"`; nightly full run.

## Verification
1. `uv run pytest -m "not slow"` green on macOS / Linux / Windows.
2. `uv run pytest -m "android and not emulator"` green wherever Android SDK installable.
3. `uv run pytest -m "apple and simulator"` green on macOS.
4. `uv run pytest --collect-only` shows expected counts per marker.
5. Coverage on `ksproject_utils` ≥ 70% (target, not hard gate).

## Progress

### ksproject (unit)
- [x] dev dependency group + pytest config
- [x] `conftest.py` with `tmp_project`, `fake_kivyschool`
- [x] `pyproject_toml` parse / defaults / `kivyschool_root` branches
- [x] `pyproject_init` round-trip
- [x] `AndroidToolchain.find_*` discovery
- [x] `ProjectTarget` settings (`DEVELOPMENT_TEAM`, entitlements, info_plist)
- [x] `setting_presets` merge
- [ ] ~~`gradle_build_files` snapshot (root + app)~~ *(N/A — emission moved to `ksp_bootstraps`; verified via Phase 3 integration instead)*

### Android — Gradle (macOS / Linux / Windows)
- [x] **G2** `global_tools=false` versions match default `.kivyschool` *(hermetic via `fake_kivyschool`)*
- [x] **G2** `global_tools=true` + `global_tools_path` override
- [x] **G3** `build.gradle` / `settings.gradle` / `local.properties` content checks
- [ ] **G3** post-build `libpython*.so` / `libSDL2*.so` / `libmain.so` in `jniLibs/<abi>/` *(scaffolded as `@slow @android`, skips when toolchain absent)*
- [ ] **G4** emulator: boot → install → launch → logcat marker → uninstall *(scaffolded as `@slow @android @emulator`, gated by `KSPROJECT_RUN_EMULATOR=1`)*

### Apple — Xcode (macOS)
- [x] **G3** `XcodeProjectBuilder._build_spec()` shape + deps (kivy/python)
- [x] **G3** `DEVELOPMENT_TEAM` wired when `[tool.kivy-school.ios].developer_team` set
- [x] **G3** folder scaffolding + `project.yml` written
- [ ] **G3** real `xcodegen` run → `.xcodeproj` exists *(scaffolded as `@slow @apple`)*
- [ ] **G3** post-build `.xcframework`s present under `Support/` *(scaffolded as `@slow @apple @simulator`)*
- [ ] **G4** iOS simulator launch + log marker *(scaffolded; needs simulator wiring)*
- [ ] **G4** macOS app launch + log marker *(scaffolded; needs launch wiring)*

### CI
- [x] `.github/workflows/tests.yml` matrix (ubuntu / macos / windows; fast on push/PR, slow on schedule/dispatch)
- [x] Cache `~/.kivyschool` per-OS
- [x] Nightly `slow` run (schedule)

## Decisions
- pytest, single `tests/` tree with sub-dirs.
- Tiered scope: fast hermetic by default; real builds + emulator/simulator behind markers.
- Dedicated minimal fixture app under `tests/fixtures/minimal_app/`; do **not** depend on evolving `test-app4` / `hello-world`.
- Out of scope: `ksproject-gui` tests (separate plan); arch matrix beyond `arm64-v8a` + `x86_64`.

## Further Considerations
1. Android SDK install in CI: prefer downloading via `ksproject` itself for end-user parity.
2. Apple signing in CI: simulator builds need no signing; device builds skipped in CI.
3. Emulator flakiness: gate emulator tests behind `KSPROJECT_RUN_EMULATOR=1` env var.
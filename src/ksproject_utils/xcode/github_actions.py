"""GitHub Actions workflow generators for Apple App Store uploads.

Rendered workflows expect the Xcode project (``project_dist/xcode``) to be
committed alongside the app sources, so CI only has to archive + upload.

Required repository secrets:

- ``APPLE_CERT_P12_BASE64`` — base64 of the Apple Distribution certificate (.p12)
- ``APPLE_CERT_PASSWORD``   — password of that .p12
- ``ASC_KEY_ID``            — App Store Connect API Key ID
- ``ASC_ISSUER_ID``         — App Store Connect API Issuer ID
- ``ASC_KEY_P8``            — raw contents of the AuthKey_*.p8 file
"""
from __future__ import annotations

from pathlib import Path

_WORKFLOW_TEMPLATE = """\
name: __TITLE__ App Store upload

on:
  push:
    tags:
      - "*"  # every new tag; narrow to e.g. "v*" if you also tag non-releases

jobs:
  upload:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Sync project (installs ksproject dev dependency)
        run: uv sync

      - name: Import signing certificate
        env:
          APPLE_CERT_P12_BASE64: ${{ secrets.APPLE_CERT_P12_BASE64 }}
          APPLE_CERT_PASSWORD: ${{ secrets.APPLE_CERT_PASSWORD }}
          KEYCHAIN_PASSWORD: ${{ github.run_id }}
        run: |
          CERT_PATH="$RUNNER_TEMP/dist.p12"
          KEYCHAIN_PATH="$RUNNER_TEMP/signing.keychain-db"
          echo -n "$APPLE_CERT_P12_BASE64" | base64 --decode -o "$CERT_PATH"
          security create-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
          security set-keychain-settings -lut 21600 "$KEYCHAIN_PATH"
          security unlock-keychain -p "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH"
          security import "$CERT_PATH" -P "$APPLE_CERT_PASSWORD" -A -t cert -f pkcs12 -k "$KEYCHAIN_PATH"
          security set-key-partition-list -S apple-tool:,apple: -k "$KEYCHAIN_PASSWORD" "$KEYCHAIN_PATH" > /dev/null
          security list-keychain -d user -s "$KEYCHAIN_PATH" login.keychain-db

      - name: Write App Store Connect API key
        env:
          ASC_KEY_P8: ${{ secrets.ASC_KEY_P8 }}
        run: |
          mkdir -p "$RUNNER_TEMP/asc"
          printf '%s' "$ASC_KEY_P8" > "$RUNNER_TEMP/asc/AuthKey.p8"

      - name: Archive and upload
        env:
          ASC_KEY_ID: ${{ secrets.ASC_KEY_ID }}
          ASC_ISSUER_ID: ${{ secrets.ASC_ISSUER_ID }}
          ASC_KEY_PATH: ${{ runner.temp }}/asc/AuthKey.p8
        run: |
          # Build number: unique and increasing per workflow run.
          # App version: taken from the tag when it looks like 1.2.3 (a
          # leading "v" is stripped); otherwise the committed value is kept.
          VERSION_ARGS=()
          TAG="${GITHUB_REF_NAME#v}"
          if [[ "$TAG" =~ ^[0-9]+(\\.[0-9]+){0,2}$ ]]; then
            VERSION_ARGS=(--app-version "$TAG")
          fi
          uv run ksproject apple __PLATFORM__ archive release --upload \\
            --build-number "${{ github.run_number }}" "${VERSION_ARGS[@]}"
"""

_TITLES = {"ios": "iOS", "macos": "macOS"}


def render_appstore_workflow(platform: str) -> str:
    """Return the workflow YAML for ``platform`` ("ios" or "macos")."""
    if platform not in _TITLES:
        raise ValueError(f"Unsupported workflow platform: {platform!r}")
    return (
        _WORKFLOW_TEMPLATE
        .replace("__TITLE__", _TITLES[platform])
        .replace("__PLATFORM__", platform)
    )


def write_appstore_workflow(project_path: Path, platform: str) -> Path:
    """Write the workflow into ``<project>/.github/workflows`` and return its path."""
    workflows = project_path / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    out = workflows / f"appstore-{platform}.yml"
    out.write_text(render_appstore_workflow(platform))
    return out

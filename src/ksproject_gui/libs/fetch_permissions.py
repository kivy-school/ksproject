import os
import json
import base64
import requests
import xml.etree.ElementTree as ET

import tempfile


class AndroidPermissionAPI:
    """
    A standalone API to fetch and cache Android permissions directly from AOSP.
    """

    AOSP_URL = "https://android.googlesource.com/platform/frameworks/base/+/master/core/res/AndroidManifest.xml?format=TEXT"

    def __init__(self, cache_filename=os.path.join(tempfile.gettempdir(), "ksproject_permissions_cache.json")):
        self.cache_file = cache_filename

    def get_permissions(self, force_refresh=False):
        """
        Retrieves the list of Android permissions.
        Returns cached data if available, otherwise fetches from AOSP.

        :param force_refresh: If True, ignores the cache and fetches fresh data.
        :return: A sorted list of permission strings.
        """
        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    permissions = json.load(f)
                if permissions:
                    return permissions
            except (json.JSONDecodeError, IOError):
                pass

        return self._fetch_and_cache()

    def _fetch_and_cache(self):
        """Internal method to fetch data from AOSP, parse it, and cache it."""
        try:
            response = requests.get(self.AOSP_URL, timeout=10)
            response.raise_for_status()

            xml_content = base64.b64decode(response.text).decode("utf-8")

            root = ET.fromstring(xml_content)
            fetched_perms = set()

            for perm in root.findall("permission"):
                name = perm.attrib.get(
                    "{http://schemas.android.com/apk/res/android}name"
                )
                if name and name.startswith("android.permission."):
                    clean_name = name.split("android.permission.")[-1]
                    fetched_perms.add(clean_name)

            all_permissions = sorted(list(fetched_perms))

            if all_permissions:
                with open(self.cache_file, "w") as f:
                    json.dump(all_permissions, f)

            return all_permissions

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch or parse Android permissions: {str(e)}"
            )

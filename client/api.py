import os
from typing import Any, Optional

import requests


class ChecklistClient:
    def __init__(self, base_url: Optional[str] = None):
        url = base_url or os.environ.get("ICPPV_SERVER_URL", "http://localhost:8000")
        self.base_url = url.rstrip("/")
        self.session = requests.Session()
        # Creating, editing and deleting items needs the server's admin login.
        password = os.environ.get("ICPPV_ADMIN_PASSWORD")
        if password:
            self.session.auth = (os.environ.get("ICPPV_ADMIN_USER", "admin"), password)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # --- read ---

    def list_items(
        self,
        type: Optional[str] = None,
        group: Optional[str] = None,
        active: Optional[bool] = None,
        activated: Optional[bool] = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if type is not None:
            params["type"] = type
        if group is not None:
            params["group"] = group
        if active is not None:
            params["active"] = str(active).lower()
        if activated is not None:
            params["activated"] = str(activated).lower()
        r = self.session.get(self._url("/items"), params=params)
        r.raise_for_status()
        return r.json()

    def get_item(self, item_id: int) -> dict:
        r = self.session.get(self._url(f"/items/{item_id}"))
        r.raise_for_status()
        return r.json()

    # --- write ---

    def create_item(
        self,
        type: str,
        group: str,
        description: str,
        active: bool = True,
        activated: bool = False,
        time: Optional[str] = None,
        sequence: Optional[int] = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "type": type,
            "group": group,
            "description": description,
            "active": active,
            "activated": activated,
        }
        if time is not None:
            payload["time"] = time
        if sequence is not None:
            payload["sequence"] = sequence
        r = self.session.post(self._url("/items"), json=payload)
        r.raise_for_status()
        return r.json()

    def update_item(self, item_id: int, **fields: Any) -> dict:
        r = self.session.put(self._url(f"/items/{item_id}"), json=fields)
        r.raise_for_status()
        return r.json()

    def set_activated(self, item_id: int, activated: bool) -> dict:
        """Mark an item done / not done (no admin login needed)."""
        r = self.session.put(self._url(f"/items/{item_id}/activated"), json={"activated": activated})
        r.raise_for_status()
        return r.json()

    def set_snooze(self, item_id: int, minutes: int) -> dict:
        """Postpone an item this many minutes past its time, 0 to undo (no admin login needed)."""
        r = self.session.put(self._url(f"/items/{item_id}/snooze"), json={"snooze": minutes})
        r.raise_for_status()
        return r.json()

    def delete_item(self, item_id: int) -> None:
        r = self.session.delete(self._url(f"/items/{item_id}"))
        r.raise_for_status()

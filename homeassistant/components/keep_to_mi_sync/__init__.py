"""The Google Keep To Mi Sync integration."""
from __future__ import annotations

import contextlib
import json
import logging

import gkeepapi

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_MASTER_TOKEN_GOOGLE,
    CONF_PASSWORD_XIAOMI,
    CONF_USERNAME_GOOGLE,
    CONF_USERNAME_XIAOMI,
    DOMAIN,
)
from .xiaomi_connector import XiaomiCloudConnector

PLATFORMS: list[Platform] = [Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Google Keep To Mi Sync from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    keepXiaomi = KeepXiaomi(entry)
    hass.data[DOMAIN][entry.entry_id] = keepXiaomi

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


class KeepXiaomi:
    """KeepXiaomi Class."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Init."""
        self.username_google = entry.data[CONF_USERNAME_GOOGLE]
        self.master_token_google = entry.data[CONF_MASTER_TOKEN_GOOGLE]
        self.username_xiaomi = entry.data[CONF_USERNAME_XIAOMI]
        self.password_xiaomi = entry.data[CONF_PASSWORD_XIAOMI]

    def add_to_mi_notes(self, items):
        """Add element to Mi Notes."""
        connector = XiaomiCloudConnector(self.username_xiaomi, self.password_xiaomi)
        connector.login()
        resp = connector.session.get("https://us.i.mi.com/todo/v1/user/records/")

        data = connector.to_json(resp.text)
        einkaufsliste = None
        if "data" in data:
            data = data["data"]
            if "records" in data:
                for record in data["records"]:
                    entity = record["contentJson"]["entity"]
                    content = connector.to_json(entity["content"])
                    if "title" in content:
                        if content["title"] == "Einkaufsliste":
                            einkaufsliste = record
                            break

        if einkaufsliste is None:
            logging.warning("Cannot find Einkaufsliste")
            return

        content = None
        with contextlib.suppress(Exception):
            content = json.loads(
                einkaufsliste["contentJson"]["entity"]["content"].replace(
                    "&&&START&&&", ""
                )
            )

        if content is None:
            logging.warning("Content is no JSON")
            return

        subEntries = content["subTodoEntities"]
        content["subTodoEntities"] = []

        for subEntry in subEntries:
            if not subEntry["isFinish"]:
                content["subTodoEntities"].append(subEntry)

        for item in items:
            content["subTodoEntities"].append({"content": item, "isFinish": False})

        einkaufsliste["contentJson"]["entity"]["content"] = json.dumps(content)
        einkaufsliste["contentJson"] = einkaufsliste["contentJson"]["entity"]

        response = connector.updateRecord(einkaufsliste)
        if "result" in connector.to_json(response.text):
            logging.info(connector.to_json(response.text)["result"])

    def sync(self):
        """Run sync."""
        keep = gkeepapi.Keep()
        keep.authenticate("blitzdose@gmail.com", self.master_token_google)

        items = []

        for note in keep.find("Einkaufsliste"):
            for item in note.unchecked:
                items.append(item.text)
                item.delete()

        if items:
            self.add_to_mi_notes(items)

        keep.sync()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

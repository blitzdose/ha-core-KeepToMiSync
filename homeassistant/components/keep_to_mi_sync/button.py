"""Sync keep Einkaufsliste to Xiaomi Cloud."""


from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KeepXiaomi
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sync Button."""
    async_add_entities([SyncButton(hass.data[DOMAIN][config_entry.entry_id])])


class SyncButton(ButtonEntity):
    """Sync Button."""

    def __init__(self, keepXiaomi: KeepXiaomi) -> None:
        """Init."""
        self._keepXiaomi = keepXiaomi
        self._attr_unique_id = keepXiaomi.username_google

    def press(self) -> None:
        """Make sync."""
        self._keepXiaomi.sync()

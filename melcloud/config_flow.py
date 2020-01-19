"""Config flow for the MELCloud platform."""
import asyncio
import logging
from typing import Callable

import pymelcloud
import voluptuous as vol
from aiohttp import ClientError, ClientResponseError
from async_timeout import timeout
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register("melcloud")
class FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _create_entry(self, email: str, token: str):
        """Register new entry."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_EMAIL, entry.title) == email:
                entry.connection_class = self.CONNECTION_CLASS
                self.hass.config_entries.async_update_entry(
                    entry, data={CONF_EMAIL: email, CONF_TOKEN: token}
                )
                return self.async_abort(
                    reason="already_configured",
                    description_placeholders={"email": email},
                )

        return self.async_create_entry(
            title=email, data={CONF_EMAIL: email, CONF_TOKEN: token}
        )

    async def _login_for_token(self, email: str, password: str) -> str:
        return await pymelcloud.login(
            email, password, self.hass.helpers.aiohttp_client.async_get_clientsession(),
        )

    async def _token_identity(self, token: str) -> str:
        print("IDENTITY")
        return token

    async def _create_client(
        self, email: str, token_provider: Callable[[], str],
    ):
        """Create client."""
        try:
            with timeout(10):
                token = await token_provider()
                print(f"TOKEN {token}")
                await pymelcloud.get_devices(
                    token, self.hass.helpers.aiohttp_client.async_get_clientsession(),
                )
        except asyncio.TimeoutError:
            return self.async_abort(reason="cannot_connect")
        except ClientResponseError as err:
            if err.status == 401 or err.status == 403:
                return self.async_abort(reason="invalid_auth")
            return self.async_abort(reason="cannot_connect")
        except ClientError:
            _LOGGER.exception("ClientError")
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error creating device")
            return self.async_abort(reason="unknown")

        return await self._create_entry(email, token)

    async def async_step_user(self, user_input=None):
        """User initiated config flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
                ),
            )
        email = user_input[CONF_EMAIL]
        return await self._create_client(
            email, lambda: self._login_for_token(email, user_input[CONF_PASSWORD])
        )

    async def async_step_import(self, user_input):
        """Import a config entry."""
        _LOGGER.info("IMPORT CALLED")
        email = user_input.get(CONF_EMAIL)
        token = user_input.get(CONF_TOKEN)
        print(f"IMPORTING {email}, {token}")
        if not token:
            return await self.async_step_user()
        return await self._create_client(email, lambda: self._token_identity(token))

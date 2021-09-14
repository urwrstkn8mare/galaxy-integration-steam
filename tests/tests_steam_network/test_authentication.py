from unittest.mock import Mock

import pytest
from galaxy.api.types import NextStep, Authentication
from galaxy.unittest.mock import async_return_value

from steam_network.protocol_client import UserActionRequired
from user_profile import ProfileIsNotPublic


@pytest.mark.parametrize('end_uri', [
    ".*login_finished.*?username=aaa&password=bbb",
    ".*two_factor_mobile_finished.*?code=aaa",
    ".*two_factor_mail_finished.*?code=aaa",
])
@pytest.mark.asyncio
async def test_public_profile_prompt_with_public_profile_with_2fa(
    plugin, profile_checker, mocker, end_uri
):
    profile_checker.check_is_public_by_steam_id.return_value = True
    mocker.patch('backend_steam_network.SteamNetworkBackend._get_websocket_auth_step',
                 return_value=async_return_value(UserActionRequired.NoActionRequired))
    plugin._SteamPlugin__backend._auth_data = [Mock(str), Mock(str)]
    result = await plugin.pass_login_credentials(
        "random step name",
        {"end_uri": f"{end_uri}"},
        {}
    )
    assert isinstance(result, Authentication)


@pytest.mark.parametrize('public_state, retry, expected_result', [
    pytest.param(True, False, Authentication, id="user with public profile clicked 'Skip' button"),
    pytest.param(False, False, Authentication, id="user with private profile clicked 'Skip' button"),
    pytest.param(True, True, Authentication, id="user with public profile clicked 'Retry' button"),
    pytest.param(False, True, NextStep, id="user with private profile clicked 'Retry' button"),
])
@pytest.mark.asyncio
async def test_public_profile_prompt_buttons(
    plugin, profile_checker, public_state, retry, expected_result
):
    profile_checker.check_is_public_by_steam_id.return_value = public_state

    result = await plugin.pass_login_credentials(
        "random step name",
        {"end_uri": f".*public_prompt_finished.*?public_profile_fallback={retry}"},
        {}
    )
    assert isinstance(result, expected_result)


@pytest.mark.parametrize('public_state, retry', [
    pytest.param(False, True),
])
@pytest.mark.asyncio
async def test_public_profile_nextstep_end_uri(
    plugin, profile_checker, public_state, retry
):
    profile_checker.check_is_public_by_steam_id.return_value = public_state

    result = await plugin.pass_login_credentials(
        "random step name",
        {"end_uri": f".*public_prompt_finished.*?public_profile_fallback={retry}"},
        {}
    )
    assert result.auth_params.get("end_uri_regex") == ".*public_prompt_finished.*"


@pytest.mark.parametrize('end_uri', [
    ".*login_finished.*?username=aaa&password=bbb",
    ".*two_factor_mobile_finished.*?code=aaa",
    ".*two_factor_mail_finished.*?code=aaa",
])
@pytest.mark.asyncio
async def test_public_profile_prompt_on_not_public_profile(
    plugin, profile_checker, mocker, end_uri
):
    profile_checker.check_is_public_by_steam_id.side_effect = ProfileIsNotPublic()
    mocker.patch('backend_steam_network.SteamNetworkBackend._get_websocket_auth_step',
                 return_value=async_return_value(UserActionRequired.NoActionRequired))
    plugin._SteamPlugin__backend._auth_data = [Mock(str), Mock(str)]
    result = await plugin.pass_login_credentials(
        "random step name",
        {"end_uri": f"{end_uri}a"},
        {}
    )
    assert isinstance(result, NextStep)
    assert "publicprofileprompt" in result.auth_params["start_uri"]

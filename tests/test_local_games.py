from galaxy.api.types import LocalGame, LocalGameState

from local_games import registry_app_dict_to_local_games_list

def test_dict_to_list_empty():
    assert registry_app_dict_to_local_games_list({}) == []

def test_dict_to_list_no_fields():
    input = {
        "1234": {
        }
    }
    expected = [LocalGame("1234", LocalGameState.None_)]
    assert expected == registry_app_dict_to_local_games_list(input)

def test_dict_to_list_no_none():
    input = {
        "1234": {
            "running": 0,
            "installed": 0,
        }
    }
    expected = [LocalGame("1234", LocalGameState.None_)]
    assert expected == registry_app_dict_to_local_games_list(input)

def test_dict_to_list_installed():
    input = {
        "1234": {
            "running": 0,
            "inStaLleD": 1,
        }
    }
    expected = [LocalGame("1234", LocalGameState.Installed)]
    assert expected == registry_app_dict_to_local_games_list(input)

def test_dict_to_list_running():
    input = {
        "1234": {
            "running": 1,
            "inStaLleD": 0,
        }
    }
    expected = [LocalGame("1234", LocalGameState.Running)]
    assert expected == registry_app_dict_to_local_games_list(input)

def test_dict_to_list_installed_and_running():
    input = {
        "1234": {
            "Running": 1,
            "inStaLleD": 1,
        }
    }
    expected = [LocalGame("1234", LocalGameState.Installed | LocalGameState.Running)]
    assert expected == registry_app_dict_to_local_games_list(input)

def test_values_as_string():
    input = {
        "1234": {
            "running": "1",
            "installed": "1",
        }
    }
    expected = [LocalGame("1234", LocalGameState.Installed | LocalGameState.Running)]
    assert expected == registry_app_dict_to_local_games_list(input)

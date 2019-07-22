import pytest
from galaxy.api.types import Achievement

from achievements_cache import as_dict, from_dict, Fingerprint
from cache import Cache


@pytest.fixture()
def dict_():
    return {
        "131": {
            "achievements": [
                {
                    "unlock_time": 1563289123,
                    "achievement_id": "abc",
                    "achievement_name": None
                },
                {
                    "unlock_time": 1563289141,
                    "achievement_id": "efg",
                    "achievement_name": None
                },
            ],
            "fingerprint": {
                "time_played": 1563289641,
                "last_played_time": 123
            }
        },
        "871": {
            "achievements": [
                {
                    "unlock_time": 156327123,
                    "achievement_id": "yik",
                    "achievement_name": "Achievement"
                }
            ],
            "fingerprint": {
                "time_played": None,
                "last_played_time": 13
            }
        }
    }


@pytest.fixture()
def cache():
    cache = Cache()
    cache.update(
        "131",
        [
            Achievement(1563289123, "abc"),
            Achievement(1563289141, "efg")
        ],
        Fingerprint(1563289641, 123)
    )
    cache.update(
        "871",
        [
            Achievement(156327123, "yik", "Achievement")
        ],
        Fingerprint(None, 13)
    )
    return cache


def test_as_dict(cache, dict_):
    assert as_dict(cache) == dict_


def test_as_dict_empty():
    assert as_dict(Cache()) == {}


def test_as_dict_not_achievement():
    cache = Cache()
    cache.update(
        "131",
        [13],
        Fingerprint(1563289641, 123)
    )
    with pytest.raises(TypeError):
        as_dict(cache)


def test_as_dict_not_fingerprint():
    cache = Cache()
    cache.update(
        "871",
        [
            Achievement(156327123, "yik", "Achievement")
        ],
        13
    )
    with pytest.raises(TypeError):
        as_dict(cache)


def test_from_dict(dict_, cache):
    assert list(from_dict(dict_)) == list(cache)


def test_from_dict_empty(dict_, cache):
    assert list(from_dict({})) == list(Cache())


@pytest.mark.parametrize(
    "dict_",
    [
        {
            "131": {}
        },
        {
            "131": {
                "fingerprint": {
                    "time_played": None,
                    "last_played_time": 13
                }
            }
        },
        {
            "131": {
                "achievements": [
                    {
                        "unlock_time": 156327123,
                        "achievement_id": "yik",
                        "achievement_name": "Achievement"
                    }
                ]
            }
        },
        {
            "871": {
                "achievements": [
                    {
                        "achievement_id": "yik",
                        "achievement_name": "Achievement"
                    }
                ],
                "fingerprint": {
                    "time_played": None,
                    "last_played_time": 13
                }
            }
        },
        {
            "871": {
                "achievements": [
                    {
                        "unlock_time": 156327123,
                        "achievement_idd": "yik",
                        "achievement_name": "Achievement"
                    }
                ],
                "fingerprint": {
                    "time_played": None,
                    "last_played_time": 13
                }
            }
        }
    ]
)
def test_from_dict_error(dict_):
    with pytest.raises(ValueError):
        from_dict(dict_)

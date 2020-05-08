import pytest

from games_cache import GamesCache
from version import __version__


@pytest.fixture
def cache():
    return GamesCache()


def test_packages_import_clean(cache):
    cache._storing_map = {'licenses':{111:{'shared': True, 'apps': {}}}}
    licenses = [{'package_id': 123,'shared': True},
                {'package_id': 321,'shared': False}]
    cache.reset_storing_map()
    cache.start_packages_import(licenses)
    exp_result = {'licenses':{123: {'shared': True, 'apps': {}},
                              321: {'shared': False, 'apps': {}}}}
    assert exp_result == cache._storing_map

def test_packages_import_additive(cache):
    cache._storing_map = {'licenses':{123:{'shared': True, 'apps': {}}}}
    licenses = [{'package_id': 321,'shared': False}]
    cache.start_packages_import(licenses)
    exp_result = {'licenses':{123: {'shared': True, 'apps': {}},
                              321: {'shared': False, 'apps': {}}}}
    assert exp_result == cache._storing_map

def test_cache_load_incompat_ver(cache):
    cache_to_load = """{"licenses": {"39661": {"shared": false, "apps": {"286000": "Tooth and Tail"}}}, "version": "0"}"""
    cache.loads(cache_to_load)
    assert not cache._storing_map


def test_cache_load_ok(cache):
    cache_to_load = """{"licenses": {"39661": {"shared": false, "apps": {"286000": "Tooth and Tail"}}}, "version": "%s"}""" % __version__
    cache.loads(cache_to_load)

    exp_result = {"licenses": {"39661": {"shared": False, "apps": {"286000": "Tooth and Tail"}}}, "version": __version__}
    assert cache._storing_map == exp_result


def test_cache_load_structure_change(cache):
    cache_to_load = """{"licenses": {"39661": { "apps": {"286000": "Tooth and Tail"}}}, "version": "%s"}""" % __version__
    cache.loads(cache_to_load)
    assert not cache._storing_map

def test_cache_dump(cache):
    cache_map = {"licenses": {"39661": {"shared": False, "apps": {"286000": "Tooth and Tail"}}}}
    cache._storing_map = cache_map
    exp_result = """{"licenses": {"39661": {"shared": false, "apps": {"286000": "Tooth and Tail"}}}, "version": "%s"}""" % __version__
    assert cache.dump() == exp_result


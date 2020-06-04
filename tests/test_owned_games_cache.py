import pytest

from games_cache import GamesCache, License, App, LicensesCache
from version import __version__


@pytest.fixture
def cache():
    return GamesCache()


def test_packages_import_clean(cache):
    cache._storing_map.licenses = [License(package_id=111, shared=True)]
    licenses = [{'package_id': 123,'shared': True},
                {'package_id': 321,'shared': False}]
    cache.reset_storing_map()
    cache.start_packages_import(licenses)
    exp_result = [License(package_id=123,shared=True), License(package_id=321, shared=False)]
    assert cache._storing_map.licenses == exp_result


def test_packages_import_additive(cache):
    cache._storing_map.licenses = [License(package_id=111, shared=True)]
    licenses = [{'package_id': 123,'shared': True},
                {'package_id': 321,'shared': False}]
    cache.start_packages_import(licenses)
    exp_result = [License(package_id=111, shared=True), License(package_id=123, shared=True), License(package_id=321, shared=False)]
    assert cache._storing_map.licenses == exp_result

def test_cache_load_incompat_ver(cache):
    cache_to_load = r"""{"licenses": "{\"licenses\": [{\"package_id\": \"39661\", \"shared\": false, \"apps\": [\"286000\"]}], \"apps\":{\"286000\": {\"appid\": \"286000\", \"title\": \"Tooth and Tail\", \"type\": \"game\"}}}"}"""
    cache.loads(cache_to_load)
    assert not cache._storing_map.licenses


def test_cache_load_ok(cache):
    cache_to_load = r"""{"licenses": "{\"licenses\": [{\"package_id\": \"39661\", \"shared\": false, \"app_ids\": [\"286000\"]}], \"apps\":{\"286000\": {\"appid\": \"286000\", \"title\": \"Tooth and Tail\", \"type\": \"game\"}}}", "version": "%s"}""" % __version__
    cache.loads(cache_to_load)

    exp_result_licenses = [License(package_id="39661", shared=False, app_ids=["286000"])]
    exp_result_apps = {"286000": App(appid="286000", title="Tooth and Tail", type="game")}
    assert cache._storing_map.licenses == exp_result_licenses
    assert cache._storing_map.apps == exp_result_apps


def test_cache_dump(cache):
    cache_map = LicensesCache()
    cache_map.licenses = [License(package_id="39661", shared=False, app_ids=["286000"])]
    cache_map.apps = {"286000": App(appid="286000", title="Tooth and Tail", type="game")}
    cache._storing_map = cache_map
    exp_result = r"""{"licenses": "{\"licenses\": [{\"package_id\": \"39661\", \"shared\": false, \"app_ids\": [\"286000\"]}], \"apps\": {\"286000\": {\"appid\": \"286000\", \"title\": \"Tooth and Tail\", \"type\": \"game\"}}}", "version": "%s"}""" % __version__
    assert cache.dump() == exp_result


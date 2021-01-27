import json
import time

from persistent_cache_state import PersistentCacheState
from websocket_cache_persistence import WebSocketCachePersistence


def test_read_does_not_modify_cache():
    address = "address_1"
    used_cell_id = 0

    persistent_cache = {
        'websocket_cache': json.dumps({used_cell_id: {'timeout': time.time() + 10, 'server': address}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    cache.read(used_cell_id)
    assert not persistent_cache_state.modified


def test_read_valid_cache_returns_address():
    address = "address_1"
    used_cell_id = 0

    persistent_cache = {
        'websocket_cache': json.dumps({used_cell_id: {'timeout': time.time() + 10, 'server': address}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(used_cell_id) == address


def test_read_no_websocket_cache_returns_none():
    used_cell_id = 0

    persistent_cache = {}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(used_cell_id) is None


def test_read_no_server_for_cell_id_returns_none():
    address = "address_1"
    saved_cell_id = 0
    read_cell_id = 1

    persistent_cache = {
        'websocket_cache': json.dumps({saved_cell_id: {'timeout': time.time() + 10, 'server': address}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(read_cell_id) is None


def test_read_no_server_entry_in_cache_returns_none():
    used_cell_id = 0

    persistent_cache = {
        'websocket_cache': json.dumps({used_cell_id: {'timeout': time.time() + 10}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(used_cell_id) is None


def test_read_no_timeout_entry_in_cache_returns_none():
    address = "address_1"
    used_cell_id = 0

    persistent_cache = {
        'websocket_cache': json.dumps({used_cell_id: {'server': address}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(used_cell_id) is None


def test_read_timeout_expired_returns_none():
    address = "address_1"
    used_cell_id = 0

    persistent_cache = {
        'websocket_cache': json.dumps({used_cell_id: {'timeout': time.time() - 10, 'server': address}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    assert cache.read(used_cell_id) is None


def test_write_modifies_cache():
    address = "address_1"
    used_cell_id = 0
    persistent_cache = dict()
    persistent_cache_state = PersistentCacheState()
    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)

    cache.write(used_cell_id, address)

    assert persistent_cache_state.modified is True


def test_write_creates_websocket_cache_when_it_does_not_exist():
    address = "address_1"
    used_cell_id = 0
    persistent_cache = dict()
    persistent_cache_state = PersistentCacheState()
    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)

    cache.write(used_cell_id, address)

    assert 'websocket_cache' in persistent_cache


def test_write_saves_server_for_specific_cell_id():
    address = "address_1"
    used_cell_id = 0
    persistent_cache = dict()
    persistent_cache_state = PersistentCacheState()
    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)

    cache.write(used_cell_id, address)

    assert json.loads(persistent_cache['websocket_cache'])[str(used_cell_id)]['server'] == address


def test_write_saves_timeout_for_specific_cell_id_30_days_in_future(monkeypatch):
    address = "address_1"
    used_cell_id = 0
    persistent_cache = dict()
    persistent_cache_state = PersistentCacheState()
    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    now = 123
    expected_timeout = now + 30 * 24 * 60 * 60

    def fake_time():
        return now

    monkeypatch.setattr(time, "time", fake_time)

    cache.write(used_cell_id, address)

    assert json.loads(persistent_cache['websocket_cache'])[str(used_cell_id)]['timeout'] == expected_timeout


def test_write_preserves_other_cell_ids():
    existing_address = "address_1"
    new_address = "address_2"
    existing_cell_id = 0
    cell_id_for_write = 1
    persistent_cache = {
        'websocket_cache': json.dumps({existing_cell_id: {'timeout': time.time() + 10, 'server': existing_address}})}
    persistent_cache_state = PersistentCacheState()
    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)

    cache.write(cell_id_for_write, new_address)

    assert json.loads(persistent_cache['websocket_cache'])[str(existing_cell_id)]['server'] == existing_address


# TODO: Temporary clean up, remove after 2021-08-01
def test_cleanup_servers_cache():
    address = "address_1"
    used_cell_id = 0

    persistent_cache = {'servers_cache': json.dumps({used_cell_id: {'timeout': time.time() + 10, 'servers': [(address, 3.206969738006592)]}})}
    persistent_cache_state = PersistentCacheState()

    cache = WebSocketCachePersistence(persistent_cache, persistent_cache_state)
    cache.write(used_cell_id, address)
    assert persistent_cache_state.modified
    assert 'servers_cache' not in persistent_cache

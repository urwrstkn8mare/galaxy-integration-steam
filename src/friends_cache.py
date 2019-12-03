import asyncio
from dataclasses import dataclass
from typing import Dict, Iterator, Tuple

from protocol.types import UserInfo


@dataclass
class AvailableInfo:
    personal_info: bool = False
    state: bool = False

    def ready(self):
        return self.personal_info and self.state


class FriendsCache:
    def __init__(self):
        self._pending_map: Dict[str, AvailableInfo] = {}
        self._user_info_map: Dict[str, UserInfo] = {}
        self._ready_event = asyncio.Event()
        self._new = True
        self.updated_handler = None
        self.added_handler = None
        self.removed_handler = None

    def reset(self, user_ids):
        new = set(user_ids)
        current = set(self._user_info_map.keys())

        for user_id in current - new:
            self._remove(user_id)

        for user_id in new - current:
            self._add(user_id)

        self._update_ready_state() # set if empty

    def add(self, user_id):
        self._add(user_id)
        self._update_ready_state()

    def remove(self, user_id):
        self._remove(user_id)
        self._update_ready_state()

    def update_info(self, user_id, user_info: UserInfo):
        current_info = self._user_info_map.get(user_id)
        if current_info is None:
            return  # not a friend, ignoring
        changed = current_info.update(user_info)

        available_info = self._pending_map.get(user_id)

        if available_info is None:
            if changed and self.updated_handler is not None:
                self.updated_handler(user_id, current_info)
        else:
            if user_info.name is not None:
                available_info.personal_info = True
            if user_info.state is not None:
                available_info.state = True
            if available_info.ready():
                del self._pending_map[user_id]
                if self.added_handler is not None:
                    self.added_handler(user_id, current_info)
                self._update_ready_state() # if pending is empty

    @property
    def ready(self):
        return self._ready_event.is_set()

    async def wait_ready(self):
        await self._ready_event.wait()

    def get(self, user_id) -> UserInfo:
        result = self._user_info_map.get(user_id)
        return result

    def user_ids(self) -> Iterator[str]:
        yield from self._user_info_map.keys()

    def __iter__(self) -> Iterator[Tuple[str, UserInfo]]:
        yield from self._user_info_map.items()

    def __contains__(self, user_id):
        return user_id in self._user_info_map

    def _add(self, user_id):
        if user_id in self._user_info_map:
            return
        self._pending_map[user_id] = AvailableInfo()
        self._user_info_map[user_id] = UserInfo()

    def _remove(self, user_id):
        pending = self._pending_map.pop(user_id, None)
        user_info = self._user_info_map.pop(user_id, None)
        if user_info is None:
            return  # user is not in cache
        if pending is None:
            # removed ready user
            if self.removed_handler is not None:
                self.removed_handler(user_id)

    def _update_ready_state(self):
        if not self._pending_map:
            self._ready_event.set()
        else:
            self._ready_event.clear()

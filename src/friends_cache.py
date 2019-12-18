from dataclasses import dataclass
from typing import Dict

from protocol.types import UserInfo
from cache_proto import ProtoCache


@dataclass
class AvailableInfo:
    personal_info: bool = False
    state: bool = False

    def ready(self):
        return self.personal_info and self.state


class FriendsCache(ProtoCache):
    def __init__(self):
        super(FriendsCache, self).__init__()
        self._pending_map: Dict[str, AvailableInfo] = {}
        self._info_map: Dict[str, UserInfo] = {}

    def _reset(self, user_ids):
        new = set(user_ids)
        current = set(self._info_map.keys())

        for user_id in current - new:
            self._remove(user_id)

        for user_id in new - current:
            self._add(user_id)

    def _add(self, user_id):
        if user_id in self._info_map:
            return
        self._pending_map[user_id] = AvailableInfo()
        self._info_map[user_id] = UserInfo()

    def _remove(self, user_id):
        pending = self._pending_map.pop(user_id, None)
        user_info = self._info_map.pop(user_id, None)
        if user_info is None:
            return  # user is not in cache
        if pending is None:
            # removed ready user
            if self.removed_handler is not None:
                self.removed_handler(user_id)

    def update(self, user_id, user_info: UserInfo):
        current_info = self._info_map.get(user_id)
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
                self._update_ready_state()  # if pending is empty

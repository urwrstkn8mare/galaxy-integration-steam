import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, NamedTuple, Optional, Set

from dataclasses_json import dataclass_json

from .cache_proto import ProtoCache

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class Achievement:
    id_: int
    name: str
    unlock_time: int


@dataclass_json
@dataclass
class Stat:
    name: str
    default: int = 0
    min: Optional[int] = None
    max: Optional[int] = None
    value: Optional[int] = None


@dataclass_json
@dataclass
class GameStats:
    game_id: int
    achievements: List[Achievement] = field(default_factory=list)
    stats: List[Stat] = field(default_factory=list)


class StatsCache(ProtoCache):
    def __init__(self):
        super(StatsCache, self).__init__()
        self._games_to_import: Set[int] = set()
        self._info_map: Dict[int, GameStats] = dict()

    def start_game_stats_import(self, game_ids: List[int]) -> Set[int]:
        """
        Adds the given game_ids to the list of games currently being imported.
        Returns the game_ids which have not yet been on the list
        """
        for game_id in game_ids:
            if game_id not in self._info_map:
                self._info_map[game_id] = GameStats(game_id=game_id)

        new_game_ids = set(game_ids).difference(self._games_to_import)
        self._games_to_import.update(game_ids)
        self._update_ready_state()
        return new_game_ids

    @property
    def import_in_progress(self):
        self._update_ready_state()
        return not self._ready_event.is_set()

    def __iter__(self):
        yield from self._info_map.items()

    def update_stats(self, game_id: int, stats: List[Stat], achievements: List[Achievement]):
        if game_id not in self._info_map:
            self._info_map[game_id] = GameStats(game_id=game_id)

        self._info_map[game_id].stats = stats
        self._info_map[game_id].achievements = achievements

        self._games_to_import.discard(game_id)
        self._update_ready_state()

    def _update_ready_state(self):
        logger.debug(f"stats import status -- apps left: {len(self._games_to_import)}")

        if len(self._games_to_import) == 0:
            if self._ready_event.is_set():
                return
            logger.info("stats import complete, setting state to ready")
            self._ready_event.set()
        else:
            self._ready_event.clear()

    def dump(self) -> str:
        return json.dumps([x.to_dict() for x in self._info_map.values()])

    def loads(self, data: str):
        for raw in json.loads(data):
            obj: GameStats = GameStats.from_dict(raw)
            self._info_map[obj.game_id] = obj

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

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
    crc_stats: int = 0


class StatsCache(ProtoCache):
    def __init__(self):
        super(StatsCache, self).__init__()
        self._games_to_import: Set[int] = set()
        self._info_map: Dict[int, GameStats] = dict()

        self._dirty: bool = False

    @property
    def dirty(self) -> bool:
        return self._dirty

    def add_games_to_import(self, game_ids: List[int]):
        """
        Adds the given game_ids to the list of games currently being imported.
        Returns the game_ids which have not yet been on the list
        """
        for game_id in game_ids:
            if game_id not in self._info_map:
                self._info_map[game_id] = GameStats(game_id=game_id)

        self._dirty = True
        self._games_to_import.update(game_ids)
        self._update_ready_state()

    def get_games_to_import(self) -> List[Tuple[int, int]]:
        """Returns tuples (game_id, crc_stats)"""
        results: List[Tuple[int, int]] = list()

        for game_id in self._games_to_import:
            stats = self._info_map.get(game_id)
            if not stats:
                # shouldn't happen but who knows
                continue

            results.append((stats.game_id, stats.crc_stats))

        return results

    @property
    def import_in_progress(self):
        self._update_ready_state()
        return not self._ready_event.is_set()

    def __iter__(self):
        yield from self._info_map.items()

    def update_stats(self, game_id: int, stats: List[Stat], achievements: List[Achievement], crc_stats: int):
        # checking for crc_stats here might break everything if my assumption is wrong. the
        # name indicates that crc_stats is a checksum over the stats data and my assumption is
        # that this value is meant to provide a short cut when checking if anything changed and
        # also to tell Steam what the latest state is we know of (and maybe only receive
        # differential data or similar). however, regardless of the crc_stats being present in
        # the request message Steam always responds with the full data set so I assume Steam
        # just ignores it. nevertheless, we can use it to reduce the amount of cache
        # invalidations whenever Galaxy asks us for achievements
        if game_id in self._info_map and self._info_map[game_id].crc_stats == crc_stats:
            # nothing changed
            self._games_to_import.discard(game_id)
            self._update_ready_state()
            return

        if game_id not in self._info_map:
            self._info_map[game_id] = GameStats(game_id=game_id)

        gameStats = self._info_map.get(game_id)
        gameStats.stats = stats
        gameStats.achievements = achievements
        gameStats.crc_stats = crc_stats

        self._dirty = True
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
        result = json.dumps([x.to_dict() for x in self._info_map.values()])
        self._dirty = False
        return result

    def loads(self, data: str):
        self._info_map = dict()
        self._dirty = False

        for raw in json.loads(data):
            obj: GameStats = GameStats.from_dict(raw)
            self._info_map[obj.game_id] = obj

from __future__ import annotations

import json
from collections import deque
from os import path
from queue import Queue
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from newTrackon.tracker import Tracker


class HistoryData(TypedDict):
    url: str
    time: int
    status: int
    ip: str
    info: list[str] | str


submitted_queue: Queue[Tracker] = Queue(maxsize=10000)
raw_history_file = "data/raw_data.json"
submitted_history_file = "data/submitted_data.json"

raw_data: deque[HistoryData] = deque(
    json.load(open(raw_history_file)) if path.exists(raw_history_file) else [],
    maxlen=600,
)
submitted_data: deque[HistoryData] = deque(
    json.load(open(submitted_history_file)) if path.exists(submitted_history_file) else [],
    maxlen=600,
)


def save_deque_to_disk(obj: deque[HistoryData], filename: str) -> None:
    json.dump(list(obj), open(filename, "w"))

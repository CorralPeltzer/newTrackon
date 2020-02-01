import os.path as path
from collections import deque
import pickle

submitted_trackers = deque(maxlen=10000)
raw_history_file = "data/raw_data.pickle"
submitted_history_file = "data/submitted_data.pickle"


if path.exists(raw_history_file):
    raw_data = pickle.load(open(raw_history_file, "rb"))
else:
    raw_data = deque(maxlen=600)
if path.exists(submitted_history_file):
    submitted_data = pickle.load(open(submitted_history_file, "rb"))
else:
    submitted_data = deque(maxlen=600)


def save_obj_to_disk(obj, filename):
    pickle.dump(obj, open(filename, "wb"))

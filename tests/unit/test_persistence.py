"""Unit tests for the persistence module."""

import json
from collections import deque


class TestDequeMaxlenValues:
    """Test that deques have correct maxlen values."""

    def test_submitted_trackers_maxlen(self):
        """Verify submitted_trackers has maxlen of 10000."""
        from newTrackon import persistence

        assert persistence.submitted_trackers.maxlen == 10000

    def test_raw_data_maxlen(self):
        """Verify raw_data has maxlen of 600."""
        from newTrackon import persistence

        assert persistence.raw_data.maxlen == 600

    def test_submitted_data_maxlen(self):
        """Verify submitted_data has maxlen of 600."""
        from newTrackon import persistence

        assert persistence.submitted_data.maxlen == 600


class TestSaveDequeToDisk:
    """Test save_deque_to_disk function."""

    def test_save_empty_deque(self, tmp_path):
        """Test saving an empty deque writes empty JSON array."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "empty.json"
        empty_deque = deque(maxlen=100)

        save_deque_to_disk(empty_deque, str(filepath))

        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert data == []

    def test_save_deque_with_strings(self, tmp_path):
        """Test saving a deque with string data."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "strings.json"
        test_deque = deque(["item1", "item2", "item3"], maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == ["item1", "item2", "item3"]

    def test_save_deque_with_dicts(self, tmp_path):
        """Test saving a deque with dictionary data."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "dicts.json"
        test_data = [
            {"url": "udp://tracker1.com:6969", "status": "success"},
            {"url": "http://tracker2.com/announce", "status": "failed"},
        ]
        test_deque = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_with_nested_data(self, tmp_path):
        """Test saving a deque with nested structures."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "nested.json"
        test_data = [
            {"tracker": "example.com", "ips": ["1.2.3.4", "5.6.7.8"], "ports": [6969]},
            {"tracker": "test.com", "ips": [], "ports": [80, 443]},
        ]
        test_deque = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_with_integers(self, tmp_path):
        """Test saving a deque with integer data."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "integers.json"
        test_deque = deque([1, 2, 3, 4, 5], maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == [1, 2, 3, 4, 5]

    def test_save_deque_overwrites_existing_file(self, tmp_path):
        """Test that saving overwrites existing file content."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "overwrite.json"
        # Write initial content
        with open(filepath, "w") as f:
            json.dump(["old", "data"], f)

        # Overwrite with new data
        new_deque = deque(["new", "content"], maxlen=100)
        save_deque_to_disk(new_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == ["new", "content"]

    def test_save_deque_creates_valid_json(self, tmp_path):
        """Test that output is valid parseable JSON."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "valid.json"
        test_deque = deque(["test"], maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        # Should not raise JSONDecodeError
        with open(filepath) as f:
            content = f.read()
        json.loads(content)


class TestDequeOverflow:
    """Test that deques correctly handle overflow at maxlen."""

    def test_submitted_trackers_overflow(self, empty_deques):
        """Test submitted_trackers removes oldest when full."""
        persistence = empty_deques
        maxlen = persistence.submitted_trackers.maxlen

        # Fill deque to capacity
        for i in range(maxlen):
            persistence.submitted_trackers.append(f"tracker_{i}")

        assert len(persistence.submitted_trackers) == maxlen
        assert persistence.submitted_trackers[0] == "tracker_0"

        # Add one more item
        persistence.submitted_trackers.append("new_tracker")

        assert len(persistence.submitted_trackers) == maxlen
        assert persistence.submitted_trackers[0] == "tracker_1"
        assert persistence.submitted_trackers[-1] == "new_tracker"

    def test_raw_data_overflow(self, empty_deques):
        """Test raw_data removes oldest when full."""
        persistence = empty_deques
        maxlen = persistence.raw_data.maxlen

        # Fill deque to capacity
        for i in range(maxlen):
            persistence.raw_data.append({"id": i})

        assert len(persistence.raw_data) == maxlen
        assert persistence.raw_data[0] == {"id": 0}

        # Add one more item
        persistence.raw_data.append({"id": maxlen})

        assert len(persistence.raw_data) == maxlen
        assert persistence.raw_data[0] == {"id": 1}
        assert persistence.raw_data[-1] == {"id": maxlen}

    def test_submitted_data_overflow(self, empty_deques):
        """Test submitted_data removes oldest when full."""
        persistence = empty_deques
        maxlen = persistence.submitted_data.maxlen

        # Fill deque to capacity
        for i in range(maxlen):
            persistence.submitted_data.append({"submission": i})

        assert len(persistence.submitted_data) == maxlen
        assert persistence.submitted_data[0] == {"submission": 0}

        # Add one more item
        persistence.submitted_data.append({"submission": maxlen})

        assert len(persistence.submitted_data) == maxlen
        assert persistence.submitted_data[0] == {"submission": 1}
        assert persistence.submitted_data[-1] == {"submission": maxlen}

    def test_deque_fifo_order_preserved(self, empty_deques):
        """Test that FIFO order is maintained during overflow."""
        test_deque = deque(maxlen=5)

        # Add items
        for i in range(10):
            test_deque.append(i)

        # Should contain last 5 items in order
        assert list(test_deque) == [5, 6, 7, 8, 9]


class TestEmptyDequeHandling:
    """Test handling of empty deques."""

    def test_empty_submitted_trackers(self, empty_deques):
        """Test empty submitted_trackers deque."""
        persistence = empty_deques

        assert len(persistence.submitted_trackers) == 0
        assert list(persistence.submitted_trackers) == []
        assert persistence.submitted_trackers.maxlen == 10000

    def test_empty_raw_data(self, empty_deques):
        """Test empty raw_data deque."""
        persistence = empty_deques

        assert len(persistence.raw_data) == 0
        assert list(persistence.raw_data) == []
        assert persistence.raw_data.maxlen == 600

    def test_empty_submitted_data(self, empty_deques):
        """Test empty submitted_data deque."""
        persistence = empty_deques

        assert len(persistence.submitted_data) == 0
        assert list(persistence.submitted_data) == []
        assert persistence.submitted_data.maxlen == 600

    def test_save_and_load_empty_deque(self, tmp_path):
        """Test saving and loading an empty deque."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "empty_test.json"
        empty_deque = deque(maxlen=600)

        save_deque_to_disk(empty_deque, str(filepath))

        with open(filepath) as f:
            loaded_data = json.load(f)

        restored_deque = deque(loaded_data, maxlen=600)
        assert len(restored_deque) == 0
        assert restored_deque.maxlen == 600


class TestLoadingBehavior:
    """Test module loading behavior with different file states."""

    def test_loading_with_existing_raw_data_file(self, tmp_path, monkeypatch):
        """Test that raw_data is loaded from file when it exists."""
        # Create test data file
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        raw_file = data_dir / "raw_data.json"
        test_data = [{"url": "tracker1.com"}, {"url": "tracker2.com"}]
        with open(raw_file, "w") as f:
            json.dump(test_data, f)

        # Monkeypatch os.path.exists and file paths before importing
        import os.path as ospath

        original_exists = ospath.exists

        def patched_exists(path):
            if path == "data/raw_data.json":
                return True
            if path == "data/submitted_data.json":
                return False
            return original_exists(path)

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path, *args, **kwargs):
            if path == "data/raw_data.json":
                return original_open(str(raw_file), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        assert len(persistence.raw_data) == 2
        assert list(persistence.raw_data) == test_data

    def test_loading_with_existing_submitted_data_file(self, tmp_path, monkeypatch):
        """Test that submitted_data is loaded from file when it exists."""
        # Create test data file
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        submitted_file = data_dir / "submitted_data.json"
        test_data = [{"result": "success"}, {"result": "failed"}]
        with open(submitted_file, "w") as f:
            json.dump(test_data, f)

        # Monkeypatch os.path.exists
        import os.path as ospath

        original_exists = ospath.exists

        def patched_exists(path):
            if path == "data/raw_data.json":
                return False
            if path == "data/submitted_data.json":
                return True
            return original_exists(path)

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path, *args, **kwargs):
            if path == "data/submitted_data.json":
                return original_open(str(submitted_file), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        assert len(persistence.submitted_data) == 2
        assert list(persistence.submitted_data) == test_data

    def test_loading_without_existing_files(self, monkeypatch):
        """Test that empty deques are created when files don't exist."""
        # Monkeypatch os.path.exists to always return False
        monkeypatch.setattr("os.path.exists", lambda path: False)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        assert len(persistence.raw_data) == 0
        assert len(persistence.submitted_data) == 0
        assert persistence.raw_data.maxlen == 600
        assert persistence.submitted_data.maxlen == 600

    def test_loaded_data_respects_maxlen(self, tmp_path, monkeypatch):
        """Test that loaded data is truncated to maxlen if file has more items."""
        # Create test data file with more than 600 items
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        raw_file = data_dir / "raw_data.json"
        test_data = [{"id": i} for i in range(700)]  # More than maxlen of 600
        with open(raw_file, "w") as f:
            json.dump(test_data, f)

        # Monkeypatch os.path.exists
        import os.path as ospath

        original_exists = ospath.exists

        def patched_exists(path):
            if path == "data/raw_data.json":
                return True
            if path == "data/submitted_data.json":
                return False
            return original_exists(path)

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path, *args, **kwargs):
            if path == "data/raw_data.json":
                return original_open(str(raw_file), *args, **kwargs)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        # Deque should only keep last 600 items
        assert len(persistence.raw_data) == 600
        assert persistence.raw_data[0] == {"id": 100}  # First 100 items discarded
        assert persistence.raw_data[-1] == {"id": 699}


class TestFilePathConstants:
    """Test file path constant values."""

    def test_raw_history_file_path(self):
        """Test raw_history_file constant value."""
        from newTrackon import persistence

        assert persistence.raw_history_file == "data/raw_data.json"

    def test_submitted_history_file_path(self):
        """Test submitted_history_file constant value."""
        from newTrackon import persistence

        assert persistence.submitted_history_file == "data/submitted_data.json"


class TestRoundTripPersistence:
    """Test saving and loading deques preserves data."""

    def test_round_trip_with_tracker_data(self, tmp_path):
        """Test that tracker data survives save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "trackers.json"
        original_data = [
            "udp://tracker1.example.com:6969/announce",
            "http://tracker2.example.com:80/announce",
            "wss://tracker3.example.com/announce",
        ]
        original_deque = deque(original_data, maxlen=10000)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data = json.load(f)

        restored_deque = deque(loaded_data, maxlen=10000)

        assert list(restored_deque) == list(original_deque)
        assert restored_deque.maxlen == original_deque.maxlen

    def test_round_trip_with_submission_data(self, tmp_path):
        """Test that submission result data survives save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "submissions.json"
        original_data = [
            {"url": "tracker1.com", "timestamp": 1700000000, "result": "added"},
            {"url": "tracker2.com", "timestamp": 1700000001, "result": "duplicate"},
            {"url": "tracker3.com", "timestamp": 1700000002, "result": "invalid"},
        ]
        original_deque = deque(original_data, maxlen=600)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data = json.load(f)

        restored_deque = deque(loaded_data, maxlen=600)

        assert list(restored_deque) == list(original_deque)

    def test_round_trip_preserves_order(self, tmp_path):
        """Test that item order is preserved through save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "ordered.json"
        original_deque = deque(range(100), maxlen=600)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data = json.load(f)

        restored_deque = deque(loaded_data, maxlen=600)

        assert list(restored_deque) == list(range(100))

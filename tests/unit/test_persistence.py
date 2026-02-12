"""Unit tests for the persistence module."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from newTrackon.persistence import HistoryData


class TestBufferMaxsizeValues:
    """Test that buffers have correct size limits."""

    def test_submitted_queue_maxsize(self) -> None:
        """Verify submitted_queue has maxsize of 10000."""
        from newTrackon import persistence

        assert persistence.submitted_queue.maxsize == 10000

    def test_raw_data_maxlen(self) -> None:
        """Verify raw_data has maxlen of 600."""
        from newTrackon import persistence

        assert persistence.raw_data.maxlen == 600

    def test_submitted_data_maxlen(self) -> None:
        """Verify submitted_data has maxlen of 600."""
        from newTrackon import persistence

        assert persistence.submitted_data.maxlen == 600


class TestSaveDequeToDisk:
    """Test save_deque_to_disk function."""

    def test_save_empty_deque(self, tmp_path: Path) -> None:
        """Test saving an empty deque writes empty JSON array."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "empty.json"
        empty_deque: deque[HistoryData] = deque(maxlen=100)

        save_deque_to_disk(empty_deque, str(filepath))

        assert filepath.exists()
        with open(filepath) as f:
            data = json.load(f)
        assert data == []

    def test_save_deque_with_history_data(self, tmp_path: Path) -> None:
        """Test saving a deque with HistoryData."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "history.json"
        test_data: list[HistoryData] = [
            {"url": "udp://tracker1.com:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": []},
            {"url": "http://tracker2.com/announce", "time": 1700000001, "status": 0, "ip": "5.6.7.8", "info": "error"},
            {"url": "wss://tracker3.com/announce", "time": 1700000002, "status": 1, "ip": "9.10.11.12", "info": []},
        ]
        test_deque: deque[HistoryData] = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_with_dicts(self, tmp_path: Path) -> None:
        """Test saving a deque with dictionary data."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "dicts.json"
        test_data: list[HistoryData] = [
            {"url": "udp://tracker1.com:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": []},
            {"url": "http://tracker2.com/announce", "time": 1700000001, "status": 0, "ip": "5.6.7.8", "info": "failed"},
        ]
        test_deque: deque[HistoryData] = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_with_nested_data(self, tmp_path: Path) -> None:
        """Test saving a deque with nested structures (info as list)."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "nested.json"
        test_data: list[HistoryData] = [
            {"url": "udp://example.com:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": ["peer1", "peer2"]},
            {"url": "http://test.com/announce", "time": 1700000001, "status": 0, "ip": "5.6.7.8", "info": []},
        ]
        test_deque: deque[HistoryData] = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_with_multiple_items(self, tmp_path: Path) -> None:
        """Test saving a deque with multiple HistoryData items."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "multiple.json"
        test_data: list[HistoryData] = [
            {"url": "udp://tracker0.com:6969", "time": 1700000000, "status": 0, "ip": "1.2.3.0", "info": []},
            {"url": "udp://tracker1.com:6969", "time": 1700000001, "status": 1, "ip": "1.2.3.1", "info": []},
            {"url": "udp://tracker2.com:6969", "time": 1700000002, "status": 0, "ip": "1.2.3.2", "info": []},
            {"url": "udp://tracker3.com:6969", "time": 1700000003, "status": 1, "ip": "1.2.3.3", "info": []},
            {"url": "udp://tracker4.com:6969", "time": 1700000004, "status": 0, "ip": "1.2.3.4", "info": []},
        ]
        test_deque: deque[HistoryData] = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == test_data

    def test_save_deque_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test that saving overwrites existing file content."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "overwrite.json"
        # Write initial content
        with open(filepath, "w") as f:
            json.dump([{"url": "old", "time": 0, "status": 0, "ip": "0.0.0.0", "info": []}], f)

        # Overwrite with new data
        new_data: list[HistoryData] = [
            {"url": "udp://new.tracker:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": []},
            {"url": "http://updated.tracker/announce", "time": 1700000001, "status": 1, "ip": "5.6.7.8", "info": []},
        ]
        new_deque: deque[HistoryData] = deque(new_data, maxlen=100)
        save_deque_to_disk(new_deque, str(filepath))

        with open(filepath) as f:
            data = json.load(f)
        assert data == new_data

    def test_save_deque_creates_valid_json(self, tmp_path: Path) -> None:
        """Test that output is valid parseable JSON."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "valid.json"
        test_data: list[HistoryData] = [
            {"url": "udp://test.tracker:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": []},
        ]
        test_deque: deque[HistoryData] = deque(test_data, maxlen=100)

        save_deque_to_disk(test_deque, str(filepath))

        # Should not raise JSONDecodeError
        with open(filepath) as f:
            content = f.read()
        json.loads(content)


class TestBufferOverflow:
    """Test that buffers correctly handle overflow at their size limits."""

    def test_submitted_queue_overflow(self, empty_queues: ModuleType) -> None:
        """Test submitted_queue rejects inserts when full."""
        from queue import Full

        persistence = empty_queues
        maxsize = persistence.submitted_queue.maxsize  # pyright: ignore[reportUnknownMemberType]

        # Fill queue to capacity
        for i in range(maxsize):  # pyright: ignore[reportUnknownArgumentType]
            persistence.submitted_queue.put_nowait(f"tracker_{i}")  # pyright: ignore[reportUnknownMemberType]

        assert persistence.submitted_queue.qsize() == maxsize  # pyright: ignore[reportUnknownMemberType]

        # Adding one more item should fail
        with pytest.raises(Full):
            persistence.submitted_queue.put_nowait("new_tracker")  # pyright: ignore[reportUnknownMemberType]

        assert persistence.submitted_queue.qsize() == maxsize  # pyright: ignore[reportUnknownMemberType]

    def test_raw_data_overflow(self, empty_queues: ModuleType) -> None:
        """Test raw_data removes oldest when full."""
        persistence = empty_queues
        maxlen = persistence.raw_data.maxlen  # pyright: ignore[reportUnknownMemberType]

        # Fill deque to capacity
        for i in range(maxlen):  # pyright: ignore[reportUnknownArgumentType]
            persistence.raw_data.append({"id": i})  # pyright: ignore[reportUnknownMemberType]

        assert len(persistence.raw_data) == maxlen  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.raw_data[0] == {"id": 0}  # pyright: ignore[reportUnknownMemberType]

        # Add one more item
        persistence.raw_data.append({"id": maxlen})  # pyright: ignore[reportUnknownMemberType]

        assert len(persistence.raw_data) == maxlen  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.raw_data[0] == {"id": 1}  # pyright: ignore[reportUnknownMemberType]
        assert persistence.raw_data[-1] == {"id": maxlen}  # pyright: ignore[reportUnknownMemberType]

    def test_submitted_data_overflow(self, empty_queues: ModuleType) -> None:
        """Test submitted_data removes oldest when full."""
        persistence = empty_queues
        maxlen = persistence.submitted_data.maxlen  # pyright: ignore[reportUnknownMemberType]

        # Fill deque to capacity
        for i in range(maxlen):  # pyright: ignore[reportUnknownArgumentType]
            persistence.submitted_data.append({"submission": i})  # pyright: ignore[reportUnknownMemberType]

        assert len(persistence.submitted_data) == maxlen  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.submitted_data[0] == {"submission": 0}  # pyright: ignore[reportUnknownMemberType]

        # Add one more item
        persistence.submitted_data.append({"submission": maxlen})  # pyright: ignore[reportUnknownMemberType]

        assert len(persistence.submitted_data) == maxlen  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.submitted_data[0] == {"submission": 1}  # pyright: ignore[reportUnknownMemberType]
        assert persistence.submitted_data[-1] == {"submission": maxlen}  # pyright: ignore[reportUnknownMemberType]

    def test_history_fifo_order_preserved(self, empty_queues: ModuleType) -> None:
        """Test that FIFO order is maintained during overflow."""
        test_buffer: deque[int] = deque(maxlen=5)

        # Add items
        for i in range(10):
            test_buffer.append(i)

        # Should contain last 5 items in order
        assert list(test_buffer) == [5, 6, 7, 8, 9]


class TestEmptyBufferHandling:
    """Test handling of empty buffers."""

    def test_empty_submitted_queue(self, empty_queues: ModuleType) -> None:
        """Test empty submitted_queue buffer."""
        persistence = empty_queues

        assert persistence.submitted_queue.qsize() == 0  # pyright: ignore[reportUnknownMemberType]
        assert persistence.submitted_queue.maxsize == 10000  # pyright: ignore[reportUnknownMemberType]

    def test_empty_raw_data(self, empty_queues: ModuleType) -> None:
        """Test empty raw_data buffer."""
        persistence = empty_queues

        assert len(persistence.raw_data) == 0  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert list(persistence.raw_data) == []  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.raw_data.maxlen == 600  # pyright: ignore[reportUnknownMemberType]

    def test_empty_submitted_data(self, empty_queues: ModuleType) -> None:
        """Test empty submitted_data buffer."""
        persistence = empty_queues

        assert len(persistence.submitted_data) == 0  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert list(persistence.submitted_data) == []  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        assert persistence.submitted_data.maxlen == 600  # pyright: ignore[reportUnknownMemberType]

    def test_save_and_load_empty_history(self, tmp_path: Path) -> None:
        """Test saving and loading an empty history buffer."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "empty_test.json"
        empty_history: deque[HistoryData] = deque(maxlen=600)

        save_deque_to_disk(empty_history, str(filepath))

        with open(filepath) as f:
            loaded_data: list[HistoryData] = json.load(f)

        restored_history: deque[HistoryData] = deque(loaded_data, maxlen=600)
        assert len(restored_history) == 0
        assert restored_history.maxlen == 600


class TestLoadingBehavior:
    """Test module loading behavior with different file states."""

    def test_loading_with_existing_raw_data_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        def patched_exists(path: str) -> bool:
            if path == "data/raw_data.json":
                return True
            if path == "data/submitted_data.json":
                return False
            return original_exists(path)  # pyright: ignore[reportReturnType]

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path: str, *args: Any, **kwargs: Any) -> Any:
            if path == "data/raw_data.json":
                result: Any = original_open(str(raw_file), *args, **kwargs)  # pyright: ignore[reportUnknownVariableType]
                return result  # pyright: ignore[reportUnknownVariableType]
            result2: Any = original_open(path, *args, **kwargs)  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
            return result2  # pyright: ignore[reportUnknownVariableType]

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        import newTrackon.ingest as ingest

        importlib.reload(ingest)

        assert len(persistence.raw_data) == 2
        assert list(persistence.raw_data) == test_data

    def test_loading_with_existing_submitted_data_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        def patched_exists(path: str) -> bool:
            if path == "data/raw_data.json":
                return False
            if path == "data/submitted_data.json":
                return True
            return original_exists(path)  # pyright: ignore[reportReturnType]

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path: str, *args: Any, **kwargs: Any) -> Any:
            if path == "data/submitted_data.json":
                result: Any = original_open(str(submitted_file), *args, **kwargs)  # pyright: ignore[reportUnknownVariableType]
                return result  # pyright: ignore[reportUnknownVariableType]
            result2: Any = original_open(path, *args, **kwargs)  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
            return result2  # pyright: ignore[reportUnknownVariableType]

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        import newTrackon.ingest as ingest

        importlib.reload(ingest)

        assert len(persistence.submitted_data) == 2
        assert list(persistence.submitted_data) == test_data

    def test_loading_without_existing_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty deques are created when files don't exist."""

        # Monkeypatch os.path.exists to always return False
        def fake_exists(path: str) -> bool:
            return False

        monkeypatch.setattr("os.path.exists", fake_exists)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        import newTrackon.ingest as ingest

        importlib.reload(ingest)

        assert len(persistence.raw_data) == 0
        assert len(persistence.submitted_data) == 0
        assert persistence.raw_data.maxlen == 600
        assert persistence.submitted_data.maxlen == 600

    def test_loaded_data_respects_maxlen(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

        def patched_exists(path: str) -> bool:
            if path == "data/raw_data.json":
                return True
            if path == "data/submitted_data.json":
                return False
            return original_exists(path)  # pyright: ignore[reportReturnType]

        monkeypatch.setattr("os.path.exists", patched_exists)

        # Monkeypatch open to redirect to our temp file
        import builtins

        original_open = builtins.open

        def patched_open(path: str, *args: Any, **kwargs: Any) -> Any:
            if path == "data/raw_data.json":
                result: Any = original_open(str(raw_file), *args, **kwargs)  # pyright: ignore[reportUnknownVariableType]
                return result  # pyright: ignore[reportUnknownVariableType]
            result2: Any = original_open(path, *args, **kwargs)  # pyright: ignore[reportCallIssue, reportUnknownVariableType]
            return result2  # pyright: ignore[reportUnknownVariableType]

        monkeypatch.setattr("builtins.open", patched_open)

        # Force reimport of the module
        import importlib

        import newTrackon.persistence as persistence

        importlib.reload(persistence)

        # Also reload trackon to update its references to the new deques
        import newTrackon.trackon as trackon

        importlib.reload(trackon)

        import newTrackon.ingest as ingest

        importlib.reload(ingest)

        # Deque should only keep last 600 items
        assert len(persistence.raw_data) == 600
        assert persistence.raw_data[0] == {"id": 100}  # First 100 items discarded
        assert persistence.raw_data[-1] == {"id": 699}


class TestFilePathConstants:
    """Test file path constant values."""

    def test_raw_history_file_path(self) -> None:
        """Test raw_history_file constant value."""
        from newTrackon import persistence

        assert persistence.raw_history_file == "data/raw_data.json"

    def test_submitted_history_file_path(self) -> None:
        """Test submitted_history_file constant value."""
        from newTrackon import persistence

        assert persistence.submitted_history_file == "data/submitted_data.json"


class TestRoundTripPersistence:
    """Test saving and loading deques preserves data."""

    def test_round_trip_with_tracker_data(self, tmp_path: Path) -> None:
        """Test that tracker data survives save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "trackers.json"
        original_data: list[HistoryData] = [
            {"url": "udp://tracker1.example.com:6969/announce", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": []},
            {"url": "http://tracker2.example.com:80/announce", "time": 1700000001, "status": 1, "ip": "5.6.7.8", "info": []},
            {"url": "wss://tracker3.example.com/announce", "time": 1700000002, "status": 1, "ip": "9.10.11.12", "info": []},
        ]
        original_deque: deque[HistoryData] = deque(original_data, maxlen=10000)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data: list[HistoryData] = json.load(f)

        restored_deque: deque[HistoryData] = deque(loaded_data, maxlen=10000)

        assert list(restored_deque) == list(original_deque)
        assert restored_deque.maxlen == original_deque.maxlen

    def test_round_trip_with_submission_data(self, tmp_path: Path) -> None:
        """Test that submission result data survives save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "submissions.json"
        original_data: list[HistoryData] = [
            {"url": "udp://tracker1.com:6969", "time": 1700000000, "status": 1, "ip": "1.2.3.4", "info": "added"},
            {"url": "udp://tracker2.com:6969", "time": 1700000001, "status": 0, "ip": "5.6.7.8", "info": "duplicate"},
            {"url": "udp://tracker3.com:6969", "time": 1700000002, "status": 0, "ip": "9.10.11.12", "info": "invalid"},
        ]
        original_deque: deque[HistoryData] = deque(original_data, maxlen=600)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data: list[HistoryData] = json.load(f)

        restored_deque: deque[HistoryData] = deque(loaded_data, maxlen=600)

        assert list(restored_deque) == list(original_deque)

    def test_round_trip_preserves_order(self, tmp_path: Path) -> None:
        """Test that item order is preserved through save/load cycle."""
        from newTrackon.persistence import save_deque_to_disk

        filepath = tmp_path / "ordered.json"
        original_data: list[HistoryData] = [
            {"url": "udp://tracker1.com:6969", "time": 1700000001, "status": 1, "ip": "1.2.3.1", "info": []},
            {"url": "udp://tracker2.com:6969", "time": 1700000002, "status": 1, "ip": "1.2.3.2", "info": []},
            {"url": "udp://tracker3.com:6969", "time": 1700000003, "status": 1, "ip": "1.2.3.3", "info": []},
            {"url": "udp://tracker4.com:6969", "time": 1700000004, "status": 1, "ip": "1.2.3.4", "info": []},
            {"url": "udp://tracker5.com:6969", "time": 1700000005, "status": 1, "ip": "1.2.3.5", "info": []},
        ]
        original_deque: deque[HistoryData] = deque(original_data, maxlen=600)

        save_deque_to_disk(original_deque, str(filepath))

        with open(filepath) as f:
            loaded_data: list[HistoryData] = json.load(f)

        restored_deque: deque[HistoryData] = deque(loaded_data, maxlen=600)

        assert list(restored_deque) == original_data

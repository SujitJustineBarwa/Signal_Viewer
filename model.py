# model.py
import redis
import time
from datetime import datetime
from typing import List, Dict, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class RedisWorker(QObject):
    """
    Worker that runs inside a QThread to poll a Redis stream
    and emits updates when data changes.
    """
    dataUpdated = pyqtSignal(str, list)  # stream_name, queue

    def __init__(self, redis_client: redis.Redis, stream: str):
        super().__init__()
        self.redis_client = redis_client
        self.stream = stream
        self._running = True
        self._last_queue: List[dict] = []

    def stop(self):
        """Signal the worker to stop gracefully."""
        self._running = False

    def run(self):
        """Main loop executed inside the QThread."""
        while self._running:
            try:
                queue = self._fetch_queue(self.stream)

                if queue != self._last_queue:
                    self._last_queue = queue
                    self.dataUpdated.emit(self.stream, queue)

            except redis.ConnectionError as e:
                print(f"[RedisWorker] Connection error: {e}, retrying...")
                time.sleep(1)
            except Exception as e:
                print(f"[RedisWorker] Error in stream {self.stream}: {e}")
                time.sleep(1)

    def _fetch_queue(self, stream: str) -> List[dict]:
        """
        Fetch last `count` items from Redis stream.
        """
        length = self.redis_client.xlen(stream)
        resp = self.redis_client.xrevrange(stream, count=length)
        queue = []
        for msg_id, fields in reversed(resp):  # chronological order
            ts_raw = fields.get(b"timestamp")
            if ts_raw:
                timestamp = datetime.strptime(ts_raw.decode(), "%Y-%m-%d %H:%M:%S")
            else:
                timestamp = datetime.now()

            queue.append({
                "id": msg_id.decode(),
                "timestamp": timestamp,
                "value": float(fields.get(b"value", 0.0)),
            })
        return queue


class RedisClient(QObject):
    """
    Redis client wrapper integrated with Qt's signal/slot system.
    Handles subscription via QThreads to avoid blocking GUI.
    """

    def __init__(self, host="localhost", port=6379, db=0):
        super().__init__()
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self._workers: Dict[str, Dict] = {}

    def list_streams(self) -> list[str]:
        """Return list of all Redis streams available."""
        stream_keys = []
        for key in self.redis_client.scan_iter():
            if self.redis_client.type(key) == b"stream":
                stream_keys.append(key.decode())
        return stream_keys

    def subscribe(self, stream: str, callback: Callable[[List[dict]], None]):
        """Subscribe to a Redis stream with updates via callback."""

        if stream in self._workers:
            print(f"[RedisClient] Already subscribed to {stream}")
            return

        worker = RedisWorker(self.redis_client, stream)
        thread = QThread()
        worker.moveToThread(thread)

        # Connect signals
        worker.dataUpdated.connect(lambda s, q: callback(stream, q))
        thread.started.connect(worker.run)

        # Track worker + thread
        self._workers[stream] = {"worker": worker, "thread": thread}

        thread.start()
        print(f"[RedisClient] Subscribed to {stream}")

    def unsubscribe(self, stream: str):
        """Unsubscribe from a Redis stream."""
        if stream not in self._workers:
            print(f"[RedisClient] Not subscribed to {stream}")
            return

        worker = self._workers[stream]["worker"]
        thread = self._workers[stream]["thread"]

        worker.stop()
        thread.quit()
        thread.wait()

        del self._workers[stream]
        print(f"[RedisClient] Unsubscribed from {stream}")

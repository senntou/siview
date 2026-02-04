from collections import deque
from PySide6.QtGui import QImage


class ImageCache:
    MAX_BYTES = 500 *  1024 * 1024  # 500MB

    def __init__(self):
        self._images: dict[str, QImage] = {}
        self._queue = deque()  # (path, bytes)
        self._current_bytes = 0

    def contains(self, path: str) -> bool:
        return path in self._images

    def get(self, path: str) -> QImage | None:
        return self._images.get(path)

    def insert(self, path: str, image: QImage) -> None:
        bytes_ = image.sizeInBytes()
        if bytes_ > self.MAX_BYTES:
            # 単体で上限超えるものは保持しない
            return

        if path in self._images:
            return  # FIFO前提、重複登録しない

        self._images[path] = image
        self._queue.append((path, bytes_))
        self._current_bytes += bytes_

        self._evict_if_needed()

    def clear(self) -> None:
        self._images.clear()
        self._queue.clear()
        self._current_bytes = 0

    @property
    def current_bytes(self) -> int:
        return self._current_bytes

    def _evict_if_needed(self) -> None:
        """FIFO方式で上限を超えたら削除する"""
        while self._current_bytes > self.MAX_BYTES and self._queue:
            path, bytes_ = self._queue.popleft()
            img = self._images.pop(path, None)
            if img is not None:
                self._current_bytes -= bytes_


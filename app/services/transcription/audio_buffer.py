import time
from collections import deque

class AudioStreamBuffer:
    def __init__(self, max_buffer_size=5, chunk_timeout=3.0):
        self.buffer = deque()
        self.last_chunk_time = None
        self.max_buffer_size = max_buffer_size
        self.chunk_timeout = chunk_timeout
        self.active = True

    def add_chunk(self, chunk):
        self.buffer.append(chunk)
        self.last_chunk_time = time.time()
        return self.should_transcribe()

    def should_transcribe(self):
        if len(self.buffer) >= self.max_buffer_size:
            return True
        if self.last_chunk_time and (time.time() - self.last_chunk_time) >= 0.5:
            return True
        return False

    def get_and_clear_chunks(self):
        chunks = list(self.buffer)
        self.buffer.clear()
        return chunks

    def has_pending_chunks(self):
        return bool(self.buffer)

    def mark_inactive(self):
        self.active = False
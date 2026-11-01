"""Source I/O fencing contract, independent real-PG reproduction."""
import sys
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg import sql

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from procurement.app import create_app
from procurement.config import Settings
from procurement.database import Database
from procurement.documents import upload, remove
from procurement.ingestion import Worker
from test_documents import MemoryBlobs, TestEmbeddings

class SimulatedProcessDeath(BaseException):
    pass

class NamedDatabase(Database):
    def __init__(self, settings, name):
        super().__init__(settings)
        self.name = name
    @contextmanager
    def connect(self):
        with super().connect() as c:
            c.execute("SELECT set_config('application_name', %s, true)", (self.name,))
            yield c

class BlockingPut(MemoryBlobs):
    def __init__(self, crash):
        super().__init__()
        self.entered, self.release, self.deleted = Event(), Event(), Event()
        self.crash = crash
    def put(self, key, body):
        self.entered.set()
        assert self.release.wait(10), 'put release timed out'
        super().put(key, body)
        if self.crash:
            raise SimulatedProcessDeath()
    def delete(self, key):
        super().delete(key)
        self.deleted.set()

@pytest.mark.parametrize('crash', [False, True], ids=['normal-rejection', 'process-death-after-put'])
def test_cleanup_fences_inflight_source_put(crash):
    settings = Settings(schema='review_source_fence_' + uuid4().hex, secret='review-' + 'x'*48)
    blobs, embeddings = BlockingPut(crash), TestEmbeddings()
    app = create_app(settings, document_blobs=blobs, document_embeddings=embeddings)
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        with TestClient(app):
            db = app.state.db
            with db.connect() as c:
                buyer = c.execute("SELECT * FROM users WHERE role='buyer'").fetchone()
            put_future = pool.submit(upload, db, blobs, buyer, str(uuid4()), 'race.txt', 'Synthetic policy', b'Synthetic policy only.')
            assert blobs.entered.wait(10)
            with db.connect() as c:
                doc = c.execute('SELECT * FROM documents').fetchone()
            # Delete must complete while external put is paused.
            remove(db, buyer, doc['id'], 1)
            cleanup_name = 'source_cleanup_' + uuid4().hex
            worker = Worker(NamedDatabase(settings, cleanup_name), blobs, embeddings)
            clean_future = pool.submit(worker.cleanup)
            deadline = time.monotonic() + 5
            waiting_for_source_lock = False
            while not blobs.deleted.is_set():
                with db.connect() as c:
                    waiting_for_source_lock = bool(c.execute("SELECT 1 FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock' AND wait_event='advisory'", (cleanup_name,)).fetchone())
                if waiting_for_source_lock:
                    break
                assert time.monotonic() < deadline, 'Cleaner neither deleted nor waited for source advisory lock'
                time.sleep(0.01)
            deleted_while_put_blocked = blobs.deleted.is_set()
            blobs.release.set()
            if crash:
                with pytest.raises(SimulatedProcessDeath):
                    put_future.result(timeout=10)
            else:
                with pytest.raises(HTTPException) as rejected:
                    put_future.result(timeout=10)
                assert rejected.value.status_code == 409
            clean_future.result(timeout=10)
            worker.cleanup()
            print({'crash': crash, 'deleted_while_put_blocked': deleted_while_put_blocked, 'advisory_wait_observed': waiting_for_source_lock, 'remaining_blobs': len(blobs.data)})
            assert not deleted_while_put_blocked, 'Cleanup performed Blob deletion while an upload could still write the same key'
            assert waiting_for_source_lock, 'Cleanup did not synchronize through the source advisory lock'
            assert not blobs.data, 'Deleted document retained late upload bytes'
    finally:
        blobs.release.set()
        pool.shutdown(wait=True)
        with app.state.db.connect() as c:
            c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(settings.schema)))

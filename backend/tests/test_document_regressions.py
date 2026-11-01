"""Independent issue #18 regression cases; external adapters are deterministic fakes.

Only UUID-prefixed schemas owned by this module are created or removed.
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/tests'))
from procurement.app import create_app
from procurement.config import Settings
from procurement.database import Database
from procurement.documents import source_text
from procurement.ingestion import Worker, LeaseLost, chunks
from test_documents import MemoryBlobs, TestEmbeddings, login, upload


@pytest.fixture
def isolated():
    settings = Settings(schema='review_regression_' + uuid4().hex, secret='review-test-' + 'x' * 48)
    blobs, embeddings = MemoryBlobs(), TestEmbeddings()
    app = create_app(settings, document_blobs=blobs, document_embeddings=embeddings)
    try:
        with TestClient(app) as client:
            yield app.state.db, client, blobs, embeddings
    finally:
        with Database(settings).connect() as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(settings.schema)))


class NamedDatabase(Database):
    """Identify the blocked publication connection through PostgreSQL activity."""
    def __init__(self, settings, name):
        super().__init__(settings)
        self.name = name

    @contextmanager
    def connect(self):
        with super().connect() as connection:
            connection.execute("SELECT set_config('application_name', %s, true)", (self.name,))
            yield connection


def test_publication_rechecks_real_lease_time_after_document_lock_wait(isolated):
    db, client, blobs, embeddings = isolated
    document = upload(client, login(client)).json()
    job = Worker(db, blobs, embeddings).claim()
    publication_name = 'review_publish_' + uuid4().hex
    worker = Worker(NamedDatabase(db.settings, publication_name), blobs, embeddings)
    with db.connect() as connection:
        version = connection.execute('SELECT * FROM document_versions WHERE id=%s', (job['version_id'],)).fetchone()
    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        with db.connect() as connection:
            connection.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()+interval '2 seconds' WHERE id=%s", (job['id'],))
        with db.connect() as blocker:
            blocker.execute('SELECT id FROM documents WHERE id=%s FOR UPDATE', (document['id'],))
            try:
                future = executor.submit(worker.publish, job, version, chunks('Synthetic policy'), embeddings.embed(['Synthetic policy']))
                deadline = time.monotonic() + 10
                with db.connect() as observer:
                    while True:
                        observer.execute('SELECT pg_stat_clear_snapshot()')
                        waiting = observer.execute("SELECT count(*) AS n FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'", (publication_name,)).fetchone()['n']
                        if waiting:
                            break
                        assert time.monotonic() < deadline, 'Publication never waited for document row lock'
                        time.sleep(0.02)
                    while True:
                        expired = observer.execute('SELECT lease_until<clock_timestamp() AS expired FROM ingestion_jobs WHERE id=%s', (job['id'],)).fetchone()['expired']
                        if expired:
                            break
                        assert time.monotonic() < deadline, 'Lease did not expire within test deadline'
                        time.sleep(0.02)
            finally:
                blocker.commit()
        with pytest.raises(LeaseLost):
            future.result(timeout=10)
        with db.connect() as connection:
            state = connection.execute('SELECT active_version FROM documents WHERE id=%s', (document['id'],)).fetchone()
            assert state['active_version'] is None
            assert connection.execute('SELECT count(*) AS n FROM document_passages').fetchone()['n'] == 0
    finally:
        executor.shutdown(wait=True)


@pytest.mark.parametrize('text', [
    ('x' * 600 + '\n') * 109,
    (('x' * 599 + '\n') * 120)[:65536],
])
def test_valid_near_limit_source_chunks_with_complete_line_coverage(text):
    content = text.encode('utf-8')
    assert 65000 < len(content) <= 65536
    assert source_text('valid-policy.txt', content) == text
    passages = chunks(text)
    assert passages
    assert all(0 < len(p['body']) <= 1200 for p in passages)
    # Chunk bodies overlap by 150 source characters; reconstruct every byte.
    rebuilt = passages[0]['body'] + ''.join(p['body'][150:] for p in passages[1:])
    assert rebuilt == text
    offset = 0
    for p in passages:
        end = offset + len(p['body'])
        assert p['line_start'] == text.count('\n', 0, offset) + 1
        assert p['line_end'] == text.count('\n', 0, end - 1) + 1
        offset = end - 150
    assert passages[0]['line_start'] == 1
    assert passages[-1]['line_end'] == text.count('\n', 0, len(text) - 1) + 1


def test_expiry_during_passage_insert_rolls_back_publication(isolated):
    db, client, blobs, embeddings = isolated
    document = upload(client, login(client)).json()
    worker = Worker(db, blobs, embeddings)
    job = worker.claim()
    with db.connect() as connection:
        version = connection.execute('SELECT * FROM document_versions WHERE id=%s', (job['version_id'],)).fetchone()
        connection.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()+interval '1 second' WHERE id=%s", (job['id'],))
        # Delay only this owned schema's insertion until actual lease expiry.
        connection.execute("""CREATE FUNCTION wait_for_publication_expiry() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE deadline timestamptz;
            BEGIN
                SELECT lease_until INTO deadline FROM ingestion_jobs WHERE version_id=NEW.version_id;
                WHILE clock_timestamp() <= deadline LOOP PERFORM pg_sleep(0.02); END LOOP;
                RETURN NEW;
            END $$""")
        connection.execute("CREATE TRIGGER publication_delay BEFORE INSERT ON document_passages FOR EACH ROW EXECUTE FUNCTION wait_for_publication_expiry()")
    with pytest.raises(LeaseLost):
        worker.publish(job, version, chunks('Synthetic policy'), embeddings.embed(['Synthetic policy']))
    with db.connect() as connection:
        assert connection.execute('SELECT active_version FROM documents WHERE id=%s', (document['id'],)).fetchone()['active_version'] is None
        assert connection.execute('SELECT count(*) AS n FROM document_passages').fetchone()['n'] == 0
        assert connection.execute('SELECT state FROM ingestion_jobs WHERE id=%s', (job['id'],)).fetchone()['state'] == 'running'

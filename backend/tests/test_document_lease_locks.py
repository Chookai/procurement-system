"""Independent lock-wait lease regressions; UUID schemas and fake providers only."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/tests'))
from test_document_regressions import isolated, NamedDatabase
from test_documents import login, upload
from procurement.ingestion import Worker, LeaseLost, chunks


def attempt_after_locked_job_expires(db, client, blobs, embeddings, action):
    document = upload(client, login(client)).json()
    job = Worker(db, blobs, embeddings).claim()
    name = 'review_job_wait_' + uuid4().hex
    worker = Worker(NamedDatabase(db.settings, name), blobs, embeddings)
    with db.connect() as connection:
        version = connection.execute('SELECT * FROM document_versions WHERE id=%s', (job['version_id'],)).fetchone()
        connection.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()+interval '2 seconds' WHERE id=%s", (job['id'],))
    with ThreadPoolExecutor(max_workers=1) as executor:
        with db.connect() as blocker:
            blocker.execute('SELECT id FROM ingestion_jobs WHERE id=%s FOR UPDATE', (job['id'],))
            try:
                if action == 'renew':
                    future = executor.submit(worker.renew, job)
                else:
                    future = executor.submit(worker.publish, job, version, chunks('Synthetic policy'), embeddings.embed(['Synthetic policy']))
                deadline = time.monotonic() + 10
                with db.connect() as observer:
                    while True:
                        observer.execute('SELECT pg_stat_clear_snapshot()')
                        waiting = observer.execute("SELECT count(*) AS n FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'", (name,)).fetchone()['n']
                        if waiting:
                            break
                        assert time.monotonic() < deadline, 'Worker never waited on the held job row lock'
                        time.sleep(0.02)
                    while not observer.execute('SELECT lease_until<clock_timestamp() AS expired FROM ingestion_jobs WHERE id=%s', (job['id'],)).fetchone()['expired']:
                        assert time.monotonic() < deadline, 'Lease did not expire before test deadline'
                        time.sleep(0.02)
            finally:
                blocker.commit()
        with pytest.raises(LeaseLost):
            future.result(timeout=10)
    with db.connect() as connection:
        assert connection.execute('SELECT lease_until<clock_timestamp() AS expired FROM ingestion_jobs WHERE id=%s', (job['id'],)).fetchone()['expired']
        assert connection.execute('SELECT active_version FROM documents WHERE id=%s', (document['id'],)).fetchone()['active_version'] is None
        assert connection.execute('SELECT count(*) AS n FROM document_passages').fetchone()['n'] == 0


def test_renewal_rechecks_expiry_after_job_row_lock_wait(isolated):
    attempt_after_locked_job_expires(*isolated, 'renew')


def test_publication_rechecks_expiry_after_job_row_lock_wait(isolated):
    attempt_after_locked_job_expires(*isolated, 'publish')

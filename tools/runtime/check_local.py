"""Exercise real local services; write only synthetic compatibility fixtures."""
import argparse
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
# Public synthetic emulator credentials; not an Azure account secret.
BLOB_KEY = 'bG9jYWwtZW11bGF0b3Itb25seQ=='
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://procurement:procurement-local-only@127.0.0.1:15432/procurement')
CONTAINER = 'runtime-compatibility'
PAYLOAD = b'PO: 10 pump seals at MYR 200; GR: 6 accepted; outstanding: 4.'


def blob_client():
    endpoint = os.getenv('BLOB_ENDPOINT', 'http://127.0.0.1:14577/devstoreaccount1')
    return BlobServiceClient(endpoint, credential={'account_name': 'devstoreaccount1', 'account_key': BLOB_KEY})


def postgres(mode):
    with psycopg.connect(DATABASE_URL, connect_timeout=5) as connection:
        connection.execute('CREATE EXTENSION IF NOT EXISTS vector')
        version = connection.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]
        server = connection.execute('SHOW server_version').fetchone()[0]
        connection.execute('CREATE SCHEMA IF NOT EXISTS runtime_probe')
        connection.execute('CREATE TABLE IF NOT EXISTS runtime_probe.persistence (id text PRIMARY KEY, payload text NOT NULL)')
        if mode == 'seed':
            connection.execute("INSERT INTO runtime_probe.persistence VALUES ('restart', %s) ON CONFLICT (id) DO UPDATE SET payload=EXCLUDED.payload", (PAYLOAD.decode(),))
        elif mode == 'verify':
            row = connection.execute("SELECT payload FROM runtime_probe.persistence WHERE id='restart'").fetchone()
            assert row and row[0] == PAYLOAD.decode(), 'Postgres restart fixture missing'
        else:
            connection.execute('CREATE TEMP TABLE passages (id int, body text, embedding vector(3))')
            connection.execute("INSERT INTO passages VALUES (1, 'pump seals accepted six', '[1,0,0]'), (2, 'catering lunch policy', '[0,1,0]')")
            assert connection.execute("SELECT id FROM passages WHERE to_tsvector('english', body) @@ plainto_tsquery('english', 'pump seals')").fetchall() == [(1,)]
            assert connection.execute("SELECT id FROM passages ORDER BY embedding <=> '[1,0,0]' LIMIT 1").fetchone() == (1,)
        return {'server': server, 'vector': version, 'mode': mode}


def job_lock():
    with psycopg.connect(DATABASE_URL, connect_timeout=5) as setup:
        setup.execute("INSERT INTO runtime_probe.persistence VALUES ('lease', 'pending') ON CONFLICT DO NOTHING")
    with psycopg.connect(DATABASE_URL, connect_timeout=5) as first, psycopg.connect(DATABASE_URL, connect_timeout=5) as second:
        assert first.execute("SELECT id FROM runtime_probe.persistence WHERE id='lease' FOR UPDATE SKIP LOCKED").fetchone() == ('lease',)
        assert second.execute("SELECT id FROM runtime_probe.persistence WHERE id='lease' FOR UPDATE SKIP LOCKED").fetchone() is None
    return {'skip_locked': True, 'scope': 'database locking primitive; not a worker implementation'}


def blob(mode):
    with blob_client() as client:
        container = client.get_container_client(CONTAINER)
        try:
            container.create_container()
        except ResourceExistsError:
            pass
        item = container.get_blob_client('restart.txt' if mode in ('seed', 'verify') else 'operations.txt')
        if mode == 'verify':
            assert item.download_blob().readall() == PAYLOAD, 'Blob restart fixture missing'
        else:
            item.upload_blob(PAYLOAD, overwrite=True, metadata={'source': 'synthetic'}, content_settings=ContentSettings(content_type='text/plain'))
            assert item.download_blob().readall() == PAYLOAD
            assert item.get_blob_properties().metadata['source'] == 'synthetic'
            assert item.download_blob(offset=0, length=6).readall() == PAYLOAD[:6]
            assert item.blob_name in [row.name for row in container.list_blobs()]
            if mode == 'exercise':
                item.upload_blob(b'replaced', overwrite=True)
                assert item.download_blob().readall() == b'replaced'
                item.delete_blob()
                try:
                    item.download_blob().readall()
                except ResourceNotFoundError:
                    pass
                else:
                    raise AssertionError('Deleted blob remained readable')
        return {'mode': mode, 'container': CONTAINER, 'sdk_operations': 'upload, metadata, download, range, list, overwrite, delete' if mode == 'exercise' else 'restart fixture'}


def api_import_contract():
    app = FastAPI()
    @app.get('/health')
    def health():
        return {'status': 'ok'}
    with TestClient(app) as client:
        assert client.get('/health').json() == {'status': 'ok'}
    return {'scope': 'FastAPI/TestClient dependency compatibility only; no procurement API yet'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['exercise','seed','verify'], default='exercise')
    args = parser.parse_args()
    results = []
    checks = [('postgres', lambda: postgres(args.mode)), ('blob', lambda: blob(args.mode))]
    if args.mode == 'exercise':
        checks += [('job_lock', job_lock), ('fastapi', api_import_contract)]
    for name, function in checks:
        start = time.monotonic()
        try:
            details = function()
            results.append({'check': name, 'status': 'passed', 'seconds': round(time.monotonic()-start, 3), 'details': details})
        except Exception as error:
            # Do not log connection strings, headers or exception bodies that could contain keys.
            results.append({'check': name, 'status': 'failed', 'error_type': type(error).__name__})
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'scope': 'local compatibility; not RAG quality', 'mode': args.mode, 'python': platform.python_version(), 'packages': {name: importlib.metadata.version(name) for name in ['agent-framework-openai','agent-framework-core','openai','azure-storage-blob','fastapi','psycopg','uvicorn']}, 'checks': results}
    target = ROOT / 'runtime-results' / f'local-{args.mode}.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if all(item['status']=='passed' for item in results) else 1)

if __name__ == '__main__':
    main()

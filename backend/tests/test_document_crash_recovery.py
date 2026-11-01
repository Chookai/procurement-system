"""Final-claim crash recovery, using candidate code and disposable UUID schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_documents import setup, env, login, upload


def test_queued_version_recovers_after_crash_immediately_after_final_claim(env):
    app, blobs, embeddings, client, worker = env
    headers = login(client)
    response = upload(client, headers)
    assert response.status_code == 202
    document = response.json()
    version_id = document['versions'][0]['id']
    with app.state.db.connect() as c:
        c.execute('UPDATE ingestion_jobs SET attempts=2 WHERE version_id=%s', (version_id,))
    job = worker.claim()
    assert job['attempts'] == 3
    # Simulate process death before run_once starts its separate processing transaction.
    with app.state.db.connect() as c:
        before = c.execute('SELECT state FROM document_versions WHERE id=%s', (version_id,)).fetchone()
        assert before['state'] == 'queued'
        c.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE id=%s", (job['id'],))
    assert worker.claim() is None
    worker.cleanup()
    details = client.get('/api/v1/documents/' + document['id']).json()
    retry = client.post('/api/v1/documents/' + document['id'] + '/retry', headers=headers)
    print('After expired final claim:', details['versions'][0], 'retry_status=', retry.status_code, 'retry_body=', retry.json())
    assert details['versions'][0]['job_state'] == 'failed'
    assert details['versions'][0]['state'] == 'failed'
    assert retry.status_code == 200
    assert worker.run_once() is True
    final = client.get('/api/v1/documents/' + document['id']).json()
    assert final['versions'][0]['state'] == 'ready'
    assert final['active_version'] == version_id

import sys,time,json,os
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
root=os.environ.get('REVIEW_CANDIDATE_ROOT',os.getcwd())
sys.path.insert(0,root+'/backend')
sys.path.insert(0,root+'/backend/tests')
from test_document_regressions import Settings,MemoryBlobs,TestEmbeddings,create_app,TestClient,login,upload,Worker,NamedDatabase,Database,sql,LeaseLost
settings=Settings(schema='review_renew_'+uuid4().hex,secret='x'*48)
b,e=MemoryBlobs(),TestEmbeddings();app=create_app(settings,document_blobs=b,document_embeddings=e)
try:
 with TestClient(app) as client:
  db=app.state.db;upload(client,login(client));job=Worker(db,b,e).claim();name='renew_'+uuid4().hex;w=Worker(NamedDatabase(settings,name),b,e)
  with db.connect() as c:c.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()+interval '2 seconds' WHERE id=%s",(job['id'],))
  with ThreadPoolExecutor(max_workers=1) as pool:
   with db.connect() as lock:
    lock.execute('SELECT id FROM ingestion_jobs WHERE id=%s FOR UPDATE',(job['id'],))
    f=pool.submit(w.renew,job);deadline=time.monotonic()+10
    with db.connect() as obs:
     while True:
      obs.execute('SELECT pg_stat_clear_snapshot()')
      if obs.execute("SELECT count(*) AS n FROM pg_stat_activity WHERE application_name=%s AND wait_event_type='Lock'",(name,)).fetchone()['n']:break
      assert time.monotonic()<deadline
      time.sleep(.02)
     while not obs.execute('SELECT lease_until<clock_timestamp() AS expired FROM ingestion_jobs WHERE id=%s',(job['id'],)).fetchone()['expired']:
      assert time.monotonic()<deadline
      time.sleep(.02)
    lock.commit()
   try:f.result(timeout=10);outcome='renewed_after_expiry'
   except LeaseLost:outcome='LeaseLost'
  with db.connect() as c:
   after=c.execute('SELECT lease_until>clock_timestamp() AS live FROM ingestion_jobs WHERE id=%s',(job['id'],)).fetchone()['live']
  print(json.dumps({'outcome':outcome,'lease_live_after':after}))
finally:
 with Database(settings).connect() as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(settings.schema)))

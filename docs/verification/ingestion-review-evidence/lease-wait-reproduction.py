import sys,time,json,threading,os
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from psycopg import sql
root=os.environ.get('REVIEW_CANDIDATE_ROOT',os.getcwd())
sys.path.insert(0,root+'/backend')
sys.path.insert(0,root+'/backend/tests')
from procurement.config import Settings
from procurement.app import create_app
from procurement.ingestion import Worker,chunks,LeaseLost
from test_documents import MemoryBlobs,TestEmbeddings,login,upload
from fastapi.testclient import TestClient
s=Settings(schema='review_spec_'+uuid4().hex,secret='x'*48)
b,e=MemoryBlobs(),TestEmbeddings();app=create_app(s,document_blobs=b,document_embeddings=e)
try:
 with TestClient(app) as client:
  d=upload(client,login(client)).json();w=Worker(app.state.db,b,e);j=w.claim()
  with app.state.db.connect() as c:
   v=c.execute('SELECT * FROM document_versions WHERE id=%s',(j['version_id'],)).fetchone()
   c.execute("UPDATE ingestion_jobs SET lease_until=clock_timestamp()+interval '2 seconds' WHERE id=%s",(j['id'],))
  result={}
  with app.state.db.connect() as block:
   block.execute('SELECT id FROM documents WHERE id=%s FOR UPDATE',(d['id'],))
   def attempt():
    try:w.publish(j,v,chunks('policy'),e.embed(['policy']));result['outcome']='published'
    except LeaseLost:result['outcome']='lease_lost'
   with ThreadPoolExecutor(max_workers=1) as pool:
    f=pool.submit(attempt)
    time.sleep(5)
    result['clock']=str(block.execute('SELECT lease_until,clock_timestamp() AS clock, now() AS transaction_start, lease_until<clock_timestamp() AS expired FROM ingestion_jobs WHERE id=%s',(j['id'],)).fetchone())
    block.commit()
    f.result(timeout=10)
  with app.state.db.connect() as c:
   result['active_version']=str(c.execute('SELECT active_version FROM documents WHERE id=%s',(d['id'],)).fetchone()['active_version'])
  print(json.dumps(result))
finally:
 with app.state.db.connect() as c:c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(s.schema)))

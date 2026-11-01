import json,time,threading,concurrent.futures
from datetime import datetime,timedelta,timezone
import jwt
errors=[]
lock=threading.Lock()
base_time=time.time();base_mono=time.monotonic();deadline=base_mono+35
key='synthetic-clock-probe-only-not-an-app-key'
def probe(worker):
 count=0;previous=time.time();backs=[]
 while time.monotonic()<deadline:
  now=datetime.now(timezone.utc)
  token=jwt.encode({'iat':now,'exp':now+timedelta(minutes=1)},key,algorithm='HS256')
  try:jwt.decode(token,key,algorithms=['HS256'])
  except jwt.PyJWTError as error:
   payload=jwt.decode(token,key,algorithms=['HS256'],options={'verify_iat':False,'verify_exp':False})
   with lock:errors.append({'error':type(error).__name__,'iat':payload['iat'],'generation_time':now.timestamp(),'observe_time':time.time(),'monotonic':time.monotonic()})
  count+=1
  current=time.time()
  if current<previous:backs.append({'previous':previous,'current':current,'backward_seconds':previous-current})
  previous=current
 return {'worker':worker,'iterations':count,'backward_samples':backs[:20],'backward_sample_count':len(backs)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(probe,range(3)))
r={'jwt_version':jwt.__version__,'start_time':base_time,'start_monotonic':base_mono,'end_time':time.time(),'end_monotonic':time.monotonic(),'errors':errors[:20],'error_count':len(errors),'workers':results}
print(json.dumps(r,indent=2))

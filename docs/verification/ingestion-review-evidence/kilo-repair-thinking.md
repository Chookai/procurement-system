--- a/backend/procurement/ingestion.py
+++ b/backend/procurement/ingestion.py
@@ -11,7 +11,14 @@
 from .documents import event, source_text
 
 LEASE_SECONDS = 120
 MAX_ATTEMPTS = 3
+
+CHUNK_CHARS = 1200
+OVERLAP_CHARS = 150
+SNAP_CHARS = 600
+MAX_SOURCE_BYTES = 65536
+MIN_ADVANCE_CHARS = SNAP_CHARS + 1 - OVERLAP_CHARS
+MAX_PASSAGES = (MAX_SOURCE_BYTES + MIN_ADVANCE_CHARS - 1) // MIN_ADVANCE_CHARS
 
 
 def chunks(text):
@@ -18,24 +25,24 @@
     text = text.replace("\r\n", "\n").replace("\r", "\n")
     result, start = [], 0
     while start < len(text):
-        end = min(start + 1200, len(text))
+        end = min(start + CHUNK_CHARS, len(text))
         if end < len(text):
-            boundary = text.rfind("\n", start + 600, end)
+            boundary = text.rfind("\n", start + SNAP_CHARS, end)
             if boundary > start:
                 end = boundary + 1
         body = text[start:end]
         if body.strip():
             result.append(
                 {
                     "body": body,
                     "line_start": text.count("\n", 0, start) + 1,
                     "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
                 }
             )
         if end == len(text):
             break
-        start = end - 150
-    if not result or len(result) > 80:
+        start = end - OVERLAP_CHARS
+    if not result or len(result) > MAX_PASSAGES:
         raise ValueError("Invalid passage count")
     return result
 
@@ -54,25 +61,25 @@
 
     def claim(self):
         with self.db.connect() as c:
             # Expired final attempts cannot remain running forever.
             c.execute(
                 """UPDATE ingestion_jobs SET state='failed',error_code='attempts_exhausted',lease_token=NULL,lease_until=NULL
-                WHERE state='running' AND lease_until<now() AND attempts >= %s""",
+                WHERE state='running' AND lease_until<clock_timestamp() AND attempts >= %s""",
                 (MAX_ATTEMPTS,),
             )
             job = c.execute(
                 """SELECT * FROM ingestion_jobs WHERE attempts<%s AND
-                ((state='queued' AND available_at<=now()) OR (state='running' AND lease_until<now()))
+                ((state='queued' AND available_at<=now()) OR (state='running' AND lease_until<clock_timestamp()))
                 ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT 1""",
                 (MAX_ATTEMPTS,),
             ).fetchone()
             if not job:
                 return None
             return c.execute(
                 """UPDATE ingestion_jobs SET state='running',attempts=attempts+1,
-                lease_token=%s,lease_until=now()+(%s * interval '1 second') WHERE id=%s RETURNING *""",
+                lease_token=%s,lease_until=clock_timestamp()+(%s * interval '1 second') WHERE id=%s RETURNING *""",
                 (uuid4(), LEASE_SECONDS, job["id"]),
             ).fetchone()
 
     def renew(self, job):
         with self.db.connect() as c:
@@ -77,9 +84,9 @@
     def renew(self, job):
         with self.db.connect() as c:
             row = c.execute(
-                """UPDATE ingestion_jobs SET lease_until=now()+(%s * interval '1 second')
-                WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>now() RETURNING id""",
+                """UPDATE ingestion_jobs SET lease_until=clock_timestamp()+(%s * interval '1 second')
+                WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>clock_timestamp() RETURNING id""",
                 (LEASE_SECONDS, job["id"], job["lease_token"]),
             ).fetchone()
             if not row:
                 raise LeaseLost()
@@ -136,11 +143,11 @@
                     "SELECT id FROM documents WHERE id=(SELECT document_id FROM document_versions WHERE id=%s) FOR UPDATE",
                     (job["version_id"],),
                 )
                 # Rollback/publication failures return to a bounded retry. No exception body is persisted.
                 updated = c.execute(
                     """UPDATE ingestion_jobs SET state=%s,error_code='ingestion_failed',
                     available_at=now()+(%s * interval '1 second'),lease_token=NULL,lease_until=NULL
-                    WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>now() RETURNING version_id""",
+                    WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>clock_timestamp() RETURNING version_id""",
                     (
                         "failed" if job["attempts"] >= MAX_ATTEMPTS else "queued",
                         2 ** job["attempts"],
@@ -164,9 +171,9 @@
                 "SELECT * FROM documents WHERE id=%s FOR UPDATE",
                 (version["document_id"],),
             ).fetchone()
             live = c.execute(
                 """SELECT id FROM ingestion_jobs WHERE id=%s AND lease_token=%s
-                AND state='running' AND lease_until>now() FOR UPDATE""",
+                AND state='running' AND lease_until>clock_timestamp() FOR UPDATE""",
                 (job["id"], job["lease_token"]),
             ).fetchone()
             if not live:
@@ -215,8 +222,15 @@
                 "UPDATE documents SET active_version=%s WHERE id=%s",
                 (version["id"], d["id"]),
             )
+            live = c.execute(
+                """SELECT id FROM ingestion_jobs WHERE id=%s AND lease_token=%s
+                AND state='running' AND lease_until>clock_timestamp() FOR UPDATE""",
+                (job["id"], job["lease_token"]),
+            ).fetchone()
+            if not live:
+                raise LeaseLost()
             c.execute(
                 "UPDATE ingestion_jobs SET state='done',lease_token=NULL,lease_until=NULL,error_code=NULL WHERE id=%s",
                 (job["id"],),
             )
             event(c, d["id"], version["id"], None, "index_published")

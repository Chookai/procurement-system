"""Bounded external I/O. Credentials and raw provider errors never enter API results."""

import hashlib
import math
import os
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings
from openai import OpenAI

MODEL = "openai/text-embedding-3-small"
DIMENSIONS = 1536
PIPELINE = "utf8-lines-chars1200-overlap150-v1:" + MODEL + ":1536:openai"
MAX_BYTES = 65536


class BlobStore:
    def __init__(self):
        endpoint = os.getenv("BLOB_ENDPOINT", "http://127.0.0.1:14577/devstoreaccount1")
        # This adapter is explicitly local. Real Azure identity is a separate integration.
        if urlparse(endpoint).hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("Local Blob adapter requires a loopback endpoint")
        self.client = BlobServiceClient(
            endpoint,
            credential={
                "account_name": "devstoreaccount1",
                "account_key": "bG9jYWwtZW11bGF0b3Itb25seQ==",
            },
            retry_total=0,
            connection_timeout=5,
            read_timeout=15,
        )
        self.container = self.client.get_container_client("procurement-documents")

    def put(self, key, content):
        try:
            self.container.create_container()
        except ResourceExistsError:
            pass
        blob = self.container.get_blob_client(key)
        try:
            blob.upload_blob(
                content,
                overwrite=False,
                metadata={"sha256": hashlib.sha256(content).hexdigest()},
                content_settings=ContentSettings(
                    content_type="text/plain; charset=utf-8"
                ),
            )
        except ResourceExistsError:
            if self.get(key) != content:
                raise ValueError("Immutable source collision") from None

    def get(self, key):
        blob = self.container.get_blob_client(key)
        if blob.get_blob_properties().size > MAX_BYTES:
            raise ValueError("Source exceeds document limit")
        return blob.download_blob(max_concurrency=1).readall()

    def delete(self, key):
        try:
            self.container.get_blob_client(key).delete_blob()
        except ResourceNotFoundError:
            pass


def validate_vectors(vectors, count):
    if len(vectors) != count:
        raise ValueError("Embedding count mismatch")
    for vector in vectors:
        if len(vector) != DIMENSIONS or not all(
            isinstance(x, (float, int)) and math.isfinite(x) for x in vector
        ):
            raise ValueError("Invalid embedding")
        if not any(vector):
            raise ValueError("Zero embedding")
    return vectors


class Embeddings:
    def embed(self, texts):
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("Embedding credentials unavailable")
        # Fixed manifest: changing model/provider requires a new pipeline and reindexing.
        with OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            timeout=20,
            max_retries=0,
        ) as client:
            response = client.embeddings.create(
                model=MODEL,
                input=texts,
                dimensions=DIMENSIONS,
                extra_body={
                    "provider": {
                        "only": ["openai"],
                        "allow_fallbacks": False,
                        "require_parameters": True,
                    }
                },
            )
        if response.model not in (MODEL, MODEL.removeprefix("openai/")):
            raise ValueError("Embedding model mismatch")
        self.last_result = {
            "reported_model": response.model,
            "usage": response.usage.model_dump() if response.usage else None,
        }
        ordered = sorted(response.data, key=lambda row: row.index)
        if [row.index for row in ordered] != list(range(len(texts))):
            raise ValueError("Embedding indices mismatch")
        return validate_vectors([row.embedding for row in ordered], len(texts))

"""Experience Memory client backed by Actian VectorAI DB.

Stores (problem, fix, worked) experiences so an agent stops re-deriving
fixes it has already found. Pattern: on failure, embed the problem and
search memory for a prior fix; if one scores above `min_score`, reuse it.
On success, upsert (problem, fix, worked=True) for next time.

--- Start the VectorAI DB container (Community Edition, free, ~5K vector cap) ---

    docker run -d --name vectorai \\
      -v ./local_data:/var/lib/actian-vectorai \\
      -p 6573-6575:6573-6575 \\
      -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \\
      actian/vectorai:latest

Ports: 6573 REST, 6574 gRPC (used below), 6575 local web UI.

Install:
    pip install actian-vectorai-client google-genai

Env:
    GEMINI_API_KEY  (https://aistudio.google.com/apikey, free tier)
"""

from __future__ import annotations

import os
import time
from typing import Any

from actian_vectorai import Distance, PointStruct, VectorAIClient, VectorParams
from google import genai
from google.genai import types as genai_types

# gemini-embedding-001 is Google's GA text embedding model. It natively
# returns 3072-dim vectors but supports Matryoshka truncation via
# output_dimensionality; Google explicitly recommends 768 / 1536 / 3072 as
# truncation targets. We pin 768 to keep vectors small given the Community
# Edition's ~5K vector cap. VERIFY: if google-genai changes the default
# model id, update EMBED_MODEL below.
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768

DOCKER_CMD = (
    "docker run -d --name vectorai \\\n"
    "  -v ./local_data:/var/lib/actian-vectorai \\\n"
    "  -p 6573-6575:6573-6575 \\\n"
    "  -e ACTIAN_VECTORAI_ACCEPT_EULA=YES \\\n"
    "  actian/vectorai:latest"
)


class MemoryUnavailable(RuntimeError):
    """Raised when the VectorAI DB container can't be reached."""


class ExperienceMemory:
    def __init__(
        self,
        host: str = "localhost:6574",
        collection: str = "agent_memory",
        dim: int = EMBED_DIM,
    ):
        self.host = host
        self.collection = collection
        self.dim = dim
        self._genai = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        try:
            self.client = VectorAIClient(host)
            self.client.health_check()
        except Exception as e:
            raise MemoryUnavailable(
                f"VectorAI DB not reachable at {host}. Start it with:\n\n"
                f"{DOCKER_CMD}\n\n(original error: {e})"
            ) from e
        self.ensure_collection()

    def _embed(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
        """All embedding calls go through here so the model can be swapped."""
        result = self._genai.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dim,
            ),
        )
        return list(result.embeddings[0].values)

    def ensure_collection(self) -> None:
        # VERIFY: collections.list() return shape (assumed objects with .name)
        existing = {c.name for c in self.client.collections.list()}
        if self.collection not in existing:
            self.client.collections.create(
                self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.Cosine),
            )

    def recall(self, problem: str, limit: int = 5, min_score: float = 0.80) -> list[dict]:
        """Semantic search for a prior fix that worked. [] if nothing scores high enough."""
        vector = self._embed(problem, task_type="RETRIEVAL_QUERY")
        results = self.client.points.search(self.collection, vector=vector, limit=limit)
        hits = []
        for r in results:
            if r.score >= min_score:
                hits.append({"id": r.id, "score": r.score, **(r.payload or {})})
        return hits

    def remember(self, problem: str, fix: str, worked: bool, meta: dict | None = None) -> str:
        vector = self._embed(problem, task_type="RETRIEVAL_DOCUMENT")
        point_id = int(time.time() * 1_000_000)  # microsecond id, avoids collisions
        payload: dict[str, Any] = {"problem": problem, "fix": fix, "worked": worked}
        if meta:
            payload.update(meta)
        self.client.points.upsert(
            self.collection, [PointStruct(id=point_id, vector=vector, payload=payload)]
        )
        return str(point_id)

    def stats(self) -> dict:
        """Count of stored experiences and how many worked, via scroll (no count API documented)."""
        total = 0
        worked = 0
        offset = None
        while True:
            # VERIFY: scroll() signature/pagination (docs show this shape, not tested live)
            page, offset = self.client.points.scroll(
                self.collection, limit=100, offset=offset, with_vectors=False, with_payload=True
            )
            for point in page:
                total += 1
                if (point.payload or {}).get("worked"):
                    worked += 1
            if offset is None:
                break
        return {"total": total, "worked": worked, "failed": total - worked}


def smoke() -> None:
    mem = ExperienceMemory(collection="agent_memory_smoke_test")
    pairs = [
        ("TypeError: 'NoneType' object is not subscriptable in login handler",
         "Add a None check before accessing response['token']"),
        ("Playwright test times out waiting for #submit-button",
         "Increase locator timeout and wait for network idle before clicking"),
        ("PostgreSQL connection refused on port 5432",
         "Start the postgres container: docker start pg-dev"),
    ]
    for problem, fix in pairs:
        mem.remember(problem, fix, worked=True)

    query = "test hangs waiting for a button to appear on the page"
    hits = mem.recall(query, limit=1, min_score=0.5)

    ok = bool(hits) and "timeout" in hits[0]["problem"].lower()
    print("PASS" if ok else "FAIL", "-", hits[0] if hits else "no hits above threshold")
    print("stats:", mem.stats())


if __name__ == "__main__":
    smoke()

"""
Pioneer (by Fastino Labs) Python client.

Pioneer is an inference + fine-tuning platform: run predictions against
GLiNER encoder models (NER/classification/structured extraction) or LLM
decoder models, and feed human corrections back in so Pioneer's Adaptive
Inference loop can retrain automatically on live traffic.

Ground truth, in order of trust:
  1. https://api.pioneer.ai/openapi.json  (live OpenAPI schema — used for the
     exact field names below; this is the actual contract the server enforces)
  2. https://docs.pioneer.ai/{quickstart,authentication,api-reference/...}.md
     (raw markdown docs, fetched directly)
  3. https://github.com/fastino-ai/pioneer-example (turned out to document a
     *different* product surface — a personalization/memory API with
     /register, /summary, /chunks, /ingest — not the inference API. Not used.)

Confirmed facts:
  Base URL:        https://api.pioneer.ai
  Auth:             X-API-Key: $PIONEER_API_KEY  (also accepted as a Bearer
                    token — OpenAPI declares both ApiKeyAuth and BearerAuth
                    as alternatives on every route — but X-API-Key is used
                    uniformly here since it works for both the native and
                    /v1/* routes).
  POST /inference                    native extraction/generation endpoint
  POST /v1/chat/completions          OpenAI-compatible chat
  GET  /v1/models                    OpenAI-compatible model list
  GET  /base-models                  Pioneer's own model catalog
  GET  /inferences                   list past inference records
  GET  /inferences/{id}              fetch one inference record
  POST /inferences/{id}/feedback     submit a correction (see below)

  inference_id location (confirmed from openapi.json component schemas):
    - Native POST /inference: `inference_id` is a TOP-LEVEL field in the
      response body for both EncoderInferenceResponse and
      GenerateInferenceResponse.
    - POST /v1/chat/completions: NOT a top-level field (OpenAI's schema
      reserves those keys). It is nested under a Pioneer-specific extension
      object: `response["x_pioneer"]["inference_id"]`. Per the schema
      description, this is `None` when the request opted out of
      persistence (`store=False`); it is present by default (`store`
      defaults to `True`).

  Feedback payload (InferenceFeedbackRequest, from openapi.json):
    {"verdict": "correct" | "incorrect", "corrected_output": <any>, "notes": str}
    # VERIFY: docs.pioneer.ai/api-reference/inference/history.md (the
    # human-readable docs page) describes the payload as a single
    # `{"correction": {...}}` field with no verdict. That directly
    # contradicts the live openapi.json, which requires `verdict` and
    # names the correction field `corrected_output`. openapi.json is the
    # actual server contract, so this client follows it — but the docs
    # page disagreeing with the live schema is worth flagging at the booth.

Install: pip install httpx
"""

from __future__ import annotations

import os

import httpx

BASE_URL = "https://api.pioneer.ai"
DEFAULT_CHAT_MODEL = "claude-haiku-4-5"  # cheap serverless decoder model, per /concepts/models


class PioneerError(RuntimeError):
    """Raised on any non-2xx response from the Pioneer API."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Pioneer API error {status_code}: {body}")


class PioneerClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("PIONEER_API_KEY")
        if not self.api_key:
            raise PioneerError(0, "Set PIONEER_API_KEY (or pass api_key=) to use PioneerClient.")
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PioneerClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _request(self, method: str, path: str, **kw) -> dict:
        try:
            resp = self._client.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise PioneerError(0, f"transport error: {e}") from e
        if resp.status_code >= 400:
            raise PioneerError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    def chat(self, messages: list[dict], model: str | None = None, **kw) -> tuple[str, str]:
        """POST /v1/chat/completions. Returns (text, inference_id).

        inference_id comes from response["x_pioneer"]["inference_id"] (see
        module docstring) and may be an empty string if the server omitted
        the x_pioneer block or persistence was disabled (store=False).
        """
        body = {"model": model or DEFAULT_CHAT_MODEL, "messages": messages, **kw}
        data = self._request("POST", "/v1/chat/completions", json=body)
        text = data["choices"][0]["message"]["content"]
        inference_id = (data.get("x_pioneer") or {}).get("inference_id") or ""
        return text, inference_id

    def feedback(self, inference_id: str, correct: bool, correction: str | None = None) -> dict:
        """POST /inferences/{id}/feedback so Pioneer's Adaptive Inference
        loop (continuous retraining on corrected live traffic) can use it.

        # VERIFY at the booth: `correction` here is typed as a plain string
        # per the required interface, but the live schema's
        # `corrected_output` field is meant to hold a JSON structure
        # matching the original task's output shape (e.g. an entities
        # list for NER, not free text). Passed through as-is; callers
        # doing structured extraction should pass a dict via **kw-style
        # direct API use of _request instead if this matters for their demo.
        """
        payload: dict = {"verdict": "correct" if correct else "incorrect"}
        if correction is not None:
            payload["corrected_output"] = correction
        return self._request("POST", f"/inferences/{inference_id}/feedback", json=payload)

    def list_models(self) -> list[str]:
        """GET /v1/models. OpenAI-compatible list shape: {"data": [{"id": ...}]}."""
        data = self._request("GET", "/v1/models")
        items = data.get("data") if isinstance(data, dict) else data
        return [m["id"] for m in (items or []) if isinstance(m, dict) and "id" in m]

    def extract(self, text: str, schema: dict, model_id: str = "fastino/gliner2-base-v1") -> dict:
        """POST /inference — native structured extraction (entities /
        classifications / structures / relations). Returns the full
        response dict, including inference_id, result, latency_ms, etc.
        """
        body = {"model_id": model_id, "text": text, "schema": schema}
        return self._request("POST", "/inference", json=body)


def smoke() -> None:
    """Tiny end-to-end check: list models, one cheap chat call, one feedback post."""
    client = PioneerClient()

    try:
        models = client.list_models()
        print(f"PASS list_models: {len(models)} models (e.g. {models[:3]})")
    except PioneerError as e:
        print(f"FAIL list_models: {e}")

    inference_id = ""
    try:
        text, inference_id = client.chat(
            [{"role": "user", "content": "Reply with exactly: PIONEER_SMOKE_OK"}],
            max_tokens=16,
        )
        print(f"PASS chat: {text!r} (inference_id={inference_id!r})")
    except PioneerError as e:
        print(f"FAIL chat: {e}")

    if inference_id:
        try:
            result = client.feedback(inference_id, correct=True)
            print(f"PASS feedback: {result}")
        except PioneerError as e:
            print(f"FAIL feedback: {e}")
    else:
        print("SKIP feedback: no inference_id captured from chat() call above")

    client.close()


if __name__ == "__main__":
    smoke()

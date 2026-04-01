"""
SSE endpoint — streams LangGraph pipeline progress to the frontend.
Frontend subscribes with EventSource after triggering /process.
"""
import asyncio
import json
import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api import progress_store

logger = structlog.get_logger()
router = APIRouter()

AGENT_LABELS = {
    "scanner": {"name": "Scanner", "model": "Gemini Flash Lite", "step": 0},
    "extractor": {"name": "Extractor", "model": "Gemini Flash", "step": 1},
    "impact_analyst": {"name": "Impact Analyst", "model": "Gemini 2.5 Pro", "step": 2},
    "action_planner": {"name": "Action Planner", "model": "Gemini Flash", "step": 3},
    "validator": {"name": "Validator", "model": "Gemini Flash", "step": 4},
}

TIMEOUT_SECONDS = 300  # 5 minutes max


@router.get("/{document_id}")
async def stream_pipeline_progress(document_id: str):
    """
    Server-Sent Events stream for pipeline progress.
    Yields one event per agent node completion, then a final 'complete' event.
    """
    async def event_generator():
        sent_idx = 0
        elapsed = 0
        poll_interval = 0.4  # 400ms polling

        # Initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'document_id': document_id})}\n\n"

        while elapsed < TIMEOUT_SECONDS:
            new_events = progress_store.get_events(document_id, after_idx=sent_idx)
            for evt in new_events:
                yield f"data: {json.dumps(evt)}\n\n"
                sent_idx += 1

            if progress_store.is_done(document_id):
                result = progress_store.get_result(document_id)
                yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
                progress_store.clear(document_id)
                return

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        yield f"data: {json.dumps({'type': 'timeout', 'document_id': document_id})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

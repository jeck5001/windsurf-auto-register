from __future__ import annotations

import json

from fastapi import APIRouter, Request, status
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api")


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(request: Request, payload: dict) -> dict:
    repo = request.app.state.repository
    task_id = repo.create_task(mode=payload["mode"], payload=payload)
    request.app.state.task_manager.wake()
    task = repo.get_task(task_id)
    return {"id": task_id, "status": task["status"], "payload": task["payload"]}


@router.post("/queue/pause")
async def pause_queue(request: Request) -> dict:
    request.app.state.task_manager.pause()
    return {"ok": True, "paused": True}


@router.post("/queue/resume")
async def resume_queue(request: Request) -> dict:
    request.app.state.task_manager.resume()
    return {"ok": True, "paused": False}


@router.post("/tasks/{task_id}/stop")
async def stop_task(request: Request, task_id: int) -> dict:
    request.app.state.repository.request_stop(task_id)
    request.app.state.task_manager.stop(task_id)
    return {"ok": True, "task_id": task_id, "status": "stop_requested"}


@router.post("/tasks/{task_id}/retry", status_code=status.HTTP_201_CREATED)
async def retry_task(request: Request, task_id: int) -> dict:
    new_task_id = request.app.state.repository.clone_task_for_retry(task_id)
    request.app.state.task_manager.wake()
    return {"ok": True, "task_id": new_task_id, "status": "queued"}


@router.get("/tasks/{task_id}/events")
async def task_events(request: Request, task_id: int) -> StreamingResponse:
    events = request.app.state.repository.list_task_events(task_id, limit=100)

    def event_stream():
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

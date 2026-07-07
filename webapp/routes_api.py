from __future__ import annotations

import json
from typing import Any

from fastapi.concurrency import run_in_threadpool
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from windsurf_auth_replay import WorkflowError

from webapp.workflow_runner import WorkflowRequest, run_workflow_once

router = APIRouter(prefix="/api")


def _account_updates_from_result(result: dict[str, Any]) -> dict[str, str]:
    updates: dict[str, str] = {}
    email = str(result.get("email") or "").strip()
    ott = str(result.get("ott") or "").strip()
    session_token = str(result.get("session_token") or "").strip()
    trial_checkout_url = str(result.get("trial_checkout_url") or "").strip()
    pool_status = str(
        ((result.get("pool_result") or {}).get("account") or {}).get("status") or ""
    ).strip()
    if email:
        updates["email"] = email
    if ott:
        updates["ott"] = ott
    if session_token:
        updates["session_token"] = session_token
    if trial_checkout_url:
        updates["trial_checkout_url"] = trial_checkout_url
    if pool_status:
        updates["pool_status"] = pool_status
    return updates


async def _run_account_action(request: Request, account_id: int, workflow_request: WorkflowRequest) -> dict:
    repo = request.app.state.repository
    try:
        result = await run_in_threadpool(
            run_workflow_once,
            workflow_request,
            lambda _event: None,
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updates = _account_updates_from_result(result)
    if updates:
        return repo.update_account(account_id, updates)
    return repo.get_account(account_id)


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


@router.patch("/accounts/{account_id}")
async def update_account(request: Request, account_id: int, payload: dict) -> dict:
    try:
        account = request.app.state.repository.update_account(account_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc
    return {"ok": True, "account": account}


@router.delete("/accounts/{account_id}")
async def delete_account(request: Request, account_id: int) -> dict:
    try:
        request.app.state.repository.delete_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc
    return {"ok": True, "account_id": account_id}


@router.post("/accounts/{account_id}/trial")
async def trigger_account_trial(request: Request, account_id: int, payload: dict | None = None) -> dict:
    try:
        account = request.app.state.repository.get_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc
    payload = payload or {}
    session_token = str(payload.get("session_token") or account.get("session_token") or "").strip()
    if not session_token:
        raise HTTPException(status_code=400, detail="No stored session token available for direct Trial")
    updated_account = await _run_account_action(
        request,
        account_id,
        WorkflowRequest(
            mode="trial",
            email=str(account.get("email") or "").strip(),
            password=str(payload.get("password") or account.get("password") or "").strip(),
            account_count=1,
            generate_trial_link=False,
            session_token=session_token,
        ),
    )
    return {"ok": True, "account": updated_account}


@router.post("/accounts/{account_id}/push")
async def push_account_to_pool(request: Request, account_id: int, payload: dict | None = None) -> dict:
    try:
        account = request.app.state.repository.get_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc
    if getattr(request.app.state, "pool_client", None) is None:
        raise HTTPException(status_code=400, detail="Pool client is not configured")
    payload = payload or {}
    ott = str(payload.get("ott") or account.get("ott") or "").strip()
    if not ott or "..." in ott:
        raise HTTPException(status_code=400, detail="No stored full OTT available for direct Push")
    label = str(payload.get("label") or account.get("email") or "").strip()
    password = str(payload.get("password") or account.get("password") or "").strip()
    updated_account = await _run_account_action(
        request,
        account_id,
        WorkflowRequest(
            mode="upload",
            email=str(account.get("email") or "").strip(),
            password=password,
            account_count=1,
            generate_trial_link=False,
            ott=ott,
            label=label,
        ),
    )
    return {"ok": True, "account": updated_account}

from fastapi import FastAPI, HTTPException

from turnstile_solver.models import SolveRequest
from turnstile_solver.service import solve_turnstile_request

app = FastAPI(title="Turnstile Solver")


@app.post("/solve")
def solve(payload: SolveRequest) -> dict[str, str]:
    try:
        token = solve_turnstile_request(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"token": token}

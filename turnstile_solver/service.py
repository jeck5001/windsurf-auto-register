from turnstile_solver.models import SolveRequest
from windsurf_auth_replay import solve_turnstile_token_with_options


def solve_turnstile_request(payload: SolveRequest) -> str:
    return solve_turnstile_token_with_options(
        site_url=payload.site_url,
        sitekey=payload.sitekey,
        browser_path=payload.browser_path,
        timeout=payload.timeout,
        headless=payload.headless,
    )

from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    site_url: str
    sitekey: str = ""
    browser_path: str = ""
    timeout: int = Field(default=90, ge=5, le=300)
    headless: bool = True

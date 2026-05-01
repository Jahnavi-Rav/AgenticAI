import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


@dataclass
class AppConfig:
    app_env: str
    deploy_region: str
    user_region: str
    require_secrets: bool
    llm_api_key: Optional[str]


class AgentRequest(BaseModel):
    prompt: str


class AgentResponse(BaseModel):
    answer: str
    region_warning: Optional[str] = None


def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        deploy_region=os.getenv("DEPLOY_REGION", "us-east"),
        user_region=os.getenv("USER_REGION", "us-east"),
        require_secrets=os.getenv("REQUIRE_SECRETS", "false").lower() == "true",
        llm_api_key=os.getenv("LLM_API_KEY"),
    )


def check_missing_secrets(config: AppConfig) -> list[str]:
    missing = []

    if not config.llm_api_key:
        missing.append("LLM_API_KEY")

    return missing


def estimate_region_latency(deploy_region: str, user_region: str) -> int:
    """
    Toy latency estimator.
    Real systems use cloud metrics, CDN logs, or tracing data.
    """

    if deploy_region == user_region:
        return 40

    same_continent = {
        ("us-east", "us-west"),
        ("us-west", "us-east"),
        ("eu-west", "eu-central"),
        ("eu-central", "eu-west"),
    }

    if (deploy_region, user_region) in same_continent:
        return 90

    return 220


def get_region_warning(config: AppConfig) -> Optional[str]:
    latency_ms = estimate_region_latency(
        config.deploy_region,
        config.user_region,
    )

    if latency_ms > 150:
        return (
            f"High region latency risk: deploy_region={config.deploy_region}, "
            f"user_region={config.user_region}, estimated_latency={latency_ms}ms"
        )

    return None


config = load_config()
missing_secrets = check_missing_secrets(config)

if config.require_secrets and missing_secrets:
    raise RuntimeError(
        f"Missing required secrets: {', '.join(missing_secrets)}"
    )


app = FastAPI(title="Dockerized Agent Service")


@app.get("/")
def root():
    return {
        "message": "Agent service is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    missing = check_missing_secrets(config)
    region_warning = get_region_warning(config)

    healthy = not (config.require_secrets and missing)

    return {
        "healthy": healthy,
        "environment": config.app_env,
        "deploy_region": config.deploy_region,
        "user_region": config.user_region,
        "missing_secrets": missing,
        "region_warning": region_warning,
    }


@app.post("/agent", response_model=AgentResponse)
def run_agent(payload: AgentRequest):
    if not payload.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    missing = check_missing_secrets(config)

    if config.require_secrets and missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required secrets: {', '.join(missing)}",
        )

    start = time.time()

    # Mock agent logic.
    # Replace this with your real LLM/tool-calling logic.
    answer = f"Agent received: {payload.prompt}"

    latency_ms = round((time.time() - start) * 1000, 2)

    region_warning = get_region_warning(config)

    return AgentResponse(
        answer=f"{answer} | latency={latency_ms}ms",
        region_warning=region_warning,
    )
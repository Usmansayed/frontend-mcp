from __future__ import annotations

import os
from typing import Any


def get_bedrock_config() -> dict[str, Any]:
    return {
        "model": os.getenv("BEDROCK_MODEL", "amazon.nova-pro-v1:0"),
        "region": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
        "aws_sso_auth": os.getenv("AWS_SSO_AUTH", "").lower() in {"1", "true", "yes"},
    }


def create_bedrock_llm(
    model: str | None = None,
    region: str | None = None,
    temperature: float = 0.2,
):
    """Create Browser Use ChatAWSBedrock for Nova / other Bedrock models."""
    cfg = get_bedrock_config()
    model = model or cfg["model"]
    region = region or cfg["region"]

    try:
        from browser_use.llm import ChatAWSBedrock
    except ImportError as exc:
        raise RuntimeError("browser-use is not installed") from exc

    kwargs: dict[str, Any] = {
        "model": model,
        "aws_region": region,
        "temperature": temperature,
        "aws_sso_auth": cfg["aws_sso_auth"],
    }
    if cfg["aws_access_key_id"] and cfg["aws_secret_access_key"]:
        kwargs["aws_access_key_id"] = cfg["aws_access_key_id"]
        kwargs["aws_secret_access_key"] = cfg["aws_secret_access_key"]
        if cfg["aws_session_token"]:
            kwargs["aws_session_token"] = cfg["aws_session_token"]
    else:
        # Fall back to boto3 default credential chain (~/.aws/credentials, SSO, etc.)
        try:
            import boto3

            session = boto3.Session(region_name=region)
            if session.get_credentials() is not None:
                kwargs["session"] = session
                kwargs["aws_sso_auth"] = True
        except ImportError:
            pass

    return ChatAWSBedrock(**kwargs)


def credentials_available() -> bool:
    cfg = get_bedrock_config()
    if cfg["aws_sso_auth"]:
        return True
    if cfg["aws_access_key_id"] and cfg["aws_secret_access_key"]:
        return True
    try:
        import boto3

        return boto3.Session().get_credentials() is not None
    except Exception:
        return False

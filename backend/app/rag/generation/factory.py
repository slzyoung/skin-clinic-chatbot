import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.models.config import AppConfig

async def get_dynamic_llm(
    session: Optional[AsyncSession] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    base_url: Optional[str] = None
) -> BaseChatModel:
    """
    Instantiates an OpenAI-compatible LLM dynamically.
    Reads provider, model_name, and api_key from AppConfig database table or falls back to environment variables.
    """
    if session is not None:
        try:
            if not api_key:
                res_key = await session.execute(select(AppConfig).where(AppConfig.key == "LLM_API_KEY"))
                key_rec = res_key.scalar_one_or_none()
                if key_rec and key_rec.value:
                    api_key = key_rec.value

            if not model_name:
                res_model = await session.execute(select(AppConfig).where(AppConfig.key == "LLM_ACTIVE_MODEL_NAME"))
                model_rec = res_model.scalar_one_or_none()
                if model_rec and model_rec.value:
                    model_name = model_rec.value

            if base_url is None:
                res_provider = await session.execute(select(AppConfig).where(AppConfig.key == "LLM_ACTIVE_PROVIDER"))
                provider_rec = res_provider.scalar_one_or_none()
                if provider_rec and provider_rec.value:
                    provider = provider_rec.value.lower()
                    if provider == "deepseek":
                        base_url = "https://api.deepseek.com/v1"
                    elif provider == "gemini":
                        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        except Exception as e:
            logger.warning(f"Error fetching LLM config from DB: {e}")

    api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or "DEFAULT_KEY"
    model_name = model_name or os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    logger.info(f"Initializing dynamic LLM: model='{model_name}', base_url='{base_url}'")

    return ChatOpenAI(
        api_key=api_key,
        model=model_name,
        base_url=base_url
    )

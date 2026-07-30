from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.api.dependencies import get_current_user, RequireAccess
from app.models.user import User
from app.models.config import AppConfig
from app.schemas.config import ConfigUpdate, ConfigResponse, LLMValidateRequest, FetchModelsRequest, ModelInfo
import urllib.request
import urllib.error
import json

router = APIRouter(prefix="/config", tags=["config"])

@router.get("/", response_model=List[ConfigResponse])
async def list_config(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(RequireAccess("configuration:read"))
):
    stmt = select(AppConfig)
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return configs

@router.put("/{key}", response_model=ConfigResponse)
async def update_config(
    key: str,
    config_in: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(RequireAccess("configuration:write"))
):
    stmt = select(AppConfig).where(AppConfig.key == key)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        # Create it if it doesn't exist
        config = AppConfig(key=key, value=config_in.value)
        db.add(config)
    else:
        config.value = config_in.value
        
    await db.commit()
    await db.refresh(config)
    return config

@router.post("/validate-llm")
async def validate_llm(req: LLMValidateRequest, current_admin: User = Depends(RequireAccess("configuration:write"))):
    provider = req.provider.lower()
    
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{req.model_name}?key={req.api_key}"
            req_obj = urllib.request.Request(url)
            with urllib.request.urlopen(req_obj, timeout=5) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Invalid API Key or Model for Gemini")
        elif provider in ["openai", "deepseek", "ollama"]:
            from app.rag.services.factory import AdapterFactory
            resolved_base_url = AdapterFactory._resolve_provider_base_url(provider)
            
            if provider == "openai":
                url = "https://api.openai.com/v1/models"
            elif provider == "deepseek":
                url = "https://api.deepseek.com/models"
            elif resolved_base_url:
                url = f"{resolved_base_url.rstrip('/')}/models"
            else:
                url = "https://api.openai.com/v1/models"
                
            headers = {"Authorization": f"Bearer {req.api_key}"}
            req_obj = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req_obj, timeout=5) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"Invalid API Key for {provider}")
                
                res_data = json.loads(response.read().decode())
                models = [m["id"] for m in res_data.get("data", [])]
                if req.model_name and models and req.model_name not in models:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Model '{req.model_name}' not found. Valid models include: {', '.join(models[:3])}..."
                    )
        else:
            raise HTTPException(status_code=400, detail="Unknown provider")
            
        return {"status": "ok", "message": "API Key and Model validated successfully."}


    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=400, detail="Invalid API Key")
        elif e.code == 404 and provider == "gemini":
            raise HTTPException(status_code=400, detail=f"Model '{req.model_name}' not found for Gemini")
        raise HTTPException(status_code=400, detail=f"Validation failed: HTTP {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"Network error during validation: {e.reason}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")

@router.post("/fetch-models", response_model=List[ModelInfo])
async def fetch_models(req: FetchModelsRequest, current_admin: User = Depends(RequireAccess("configuration:write"))):
    provider = req.provider.lower()
    
    try:
        models = []
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={req.api_key}"
            req_obj = urllib.request.Request(url)
            with urllib.request.urlopen(req_obj, timeout=5) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail="Invalid API Key for Gemini")
                res_data = json.loads(response.read().decode())
                for m in res_data.get("models", []):
                    # Only include models that support standard text generation
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" not in methods:
                        continue
                        
                    # Gemini model names start with 'models/' so we strip it for simplicity
                    model_id = m.get("name", "").replace("models/", "")
                    
                    # Strictly filter for only gemini base models (exclude nano/experimental/bison)
                    if not model_id.startswith("gemini-"):
                        continue
                    
                    # Exclude vision models if strictly text only
                    if "vision" in model_id:
                        continue
                        
                    models.append(ModelInfo(
                        id=model_id,
                        input_limit=m.get("inputTokenLimit"),
                        output_limit=m.get("outputTokenLimit")
                    ))
        elif provider in ["openai", "deepseek", "ollama"]:
            from app.rag.services.factory import AdapterFactory
            resolved_base_url = AdapterFactory._resolve_provider_base_url(provider)
            
            if provider == "openai":
                url = "https://api.openai.com/v1/models"
            elif provider == "deepseek":
                url = "https://api.deepseek.com/models"
            elif resolved_base_url:
                url = f"{resolved_base_url.rstrip('/')}/models"
            else:
                url = "https://api.openai.com/v1/models"
                
            headers = {"Authorization": f"Bearer {req.api_key}"}
            req_obj = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req_obj, timeout=5) as response:
                if response.status != 200:
                    raise HTTPException(status_code=400, detail=f"Invalid API Key for {provider}")
                res_data = json.loads(response.read().decode())
                excluded_keywords = [
                    "tts", "whisper", "dall-e", "embedding", "babbage", 
                    "davinci", "ada", "curie", "vision", "audio", "realtime"
                ]
                
                for m in res_data.get("data", []):
                    model_id = m.get("id")
                    
                    if provider == "openai":
                        # Exclude non-text/legacy models dynamically
                        if any(keyword in model_id.lower() for keyword in excluded_keywords):
                            continue
                            
                    if provider == "deepseek":
                        # Deepseek models are mostly text, but just in case
                        if "embedding" in model_id.lower():
                            continue
                            
                    models.append(ModelInfo(id=model_id))
        else:
            raise HTTPException(status_code=400, detail="Unknown provider")
            
        return models

    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=400, detail="Invalid API Key")
        raise HTTPException(status_code=400, detail=f"Failed to fetch models: HTTP {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"Network error: {e.reason}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch models: {str(e)}")


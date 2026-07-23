from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.api.dependencies import require_admin_role
from app.models.user import User
from app.models.config import AppConfig
from app.schemas.config import ConfigUpdate, ConfigResponse, LLMValidateRequest
import urllib.request
import urllib.error
import json

router = APIRouter(prefix="/config", tags=["config"])

@router.get("/", response_model=List[ConfigResponse])
async def list_config(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role)
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
    current_admin: User = Depends(require_admin_role)
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
async def validate_llm(req: LLMValidateRequest, current_admin: User = Depends(require_admin_role)):
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

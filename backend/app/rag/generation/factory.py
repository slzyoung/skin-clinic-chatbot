from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_dynamic_llm(api_key: str, model_name: str, base_url: str = None) -> BaseChatModel:
    """
    Instantiates any OpenAI-compatible LLM fully dynamically.
    No if/else required. The dashboard or database simply passes the correct base_url.
    - OpenAI: base_url = None
    - DeepSeek: base_url = "https://api.deepseek.com/v1"
    - Gemini: base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    """
    return ChatOpenAI(
        api_key=api_key, 
        model=model_name,
        base_url=base_url
    )

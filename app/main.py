import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.orchestrator import Orchestrator
from app.services.ai_service import AIService
from app.services.kb_service import KnowledgeBase


app = FastAPI(
    title='NLP Parameter Extractor API',
    description='API для извлечения параметров товаров из текста пользователя',
    version='1.0.0'
)

# Инициализация сервисов с проверкой файлов
try:
    kb_service = KnowledgeBase()
    kb_service.load_data()
    ai_service = AIService()
    orchestrator = Orchestrator(ai_service, kb_service)
except FileNotFoundError as e:
    raise HTTPException(status_code=500, detail="Database or config files missing")


class ExtractRequest(BaseModel):
    text: str = "Нужен кожаный диван 2 метра на 2 секции"


class ExtractResponse(BaseModel):
    status: str
    category_name: Optional[str]
    category_id: Optional[str]
    parameters: List[Dict[str, Any]]
    price_min: Optional[int]
    price_max: Optional[int]
    debug_info: Optional[str]


@app.post('/extract', response_model=ExtractResponse)
async def extract_params(request: ExtractRequest) -> ExtractResponse:
    """
    Извлекает параметры товара из текста пользователя.
    
    Принимает JSON с текстом и возвращает JSON с результатами обработки.
    """
    try:
        result = await orchestrator.process_request(request.text)
        return ExtractResponse(**result)
    except Exception as e:
        return ExtractResponse(
            status='error',
            category_name=None,
            category_id=None,
            parameters=[],
            price_min=None,
            price_max=None,
            debug_info=f'Error: {str(e)}'
        )


@app.get('/health')
async def health_check() -> Dict[str, str]:
    """Проверка здоровья сервиса."""
    return {'status': 'ok', 'service': 'nlp-parameter-extractor'}


@app.get('/')
async def root() -> Dict[str, str]:
    """Корневой эндпоинт."""
    return {
        'message': 'NLP Parameter Extractor API',
        'version': '1.0.0',
        'endpoints': {
            'POST /extract': 'Извлечение параметров из текста',
            'GET /health': 'Проверка здоровья сервиса',
            'GET /docs': 'Интерактивная документация (Swagger)'
        }
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

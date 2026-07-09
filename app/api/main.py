from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from app.api.schemas import ExtractionRequest, ExtractionResponse
from app.core.orchestrator import Orchestrator
from app.services.ai_service import AIService
from app.services.kb_service import KnowledgeBase

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb_service = KnowledgeBase()
    kb_service.load_data("data/db.xlsx")
    ai_service = AIService()
    orchestrator = Orchestrator(ai_service, kb_service)
    app.state.orchestrator = orchestrator
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/extract", response_model=ExtractionResponse)
async def extract(request: ExtractionRequest):
    result = await app.state.orchestrator.process_request(request.text)
    return ExtractionResponse(**result)

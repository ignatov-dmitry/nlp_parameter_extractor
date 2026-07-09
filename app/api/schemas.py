from typing import List, Optional

from pydantic import BaseModel


class ExtractionRequest(BaseModel):
    text: str


class ParameterItem(BaseModel):
    name: str
    value: List[str]
    value_id: Optional[str] = None
    param_id: Optional[str] = None


class ExtractionResponse(BaseModel):
    status: str
    category_name: Optional[str] = None
    category_id: Optional[str] = None
    parameters: List[ParameterItem]
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    debug_info: Optional[str] = None

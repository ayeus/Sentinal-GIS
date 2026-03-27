from pydantic import BaseModel

from typing import Optional

class PredictionRequest(BaseModel):
    year: int
    disease: Optional[str] = None


class PredictionResponse(BaseModel):
    results: list
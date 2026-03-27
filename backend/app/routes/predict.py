from fastapi import APIRouter
from app.schemas.request_response import PredictionRequest
from app.services.predictor import predict_risk

router = APIRouter()

@router.post("/predict")
def predict(request: PredictionRequest):
    year = request.year
    disease = request.disease
    
    results = predict_risk(year, disease)
    
    return {"results": results}
# backend/services/adcopy_service.py
from backend.models.adcopy_model import (
    AdcopyTextRequest, AdcopyTextResponse, AdcopyImageResponse
)
from backend.models import create_text_model as text_model
from backend.models import image_text_model as image_model

def generate_text(req: AdcopyTextRequest) -> AdcopyTextResponse:
    result = text_model.generate_ad_copies(
        product=req.product,
        tone=req.tone,
        length=req.length,
        num_copies=req.num_copies,
        model=req.model,
    )
    return AdcopyTextResponse(
        raw_output=result.get("raw_output"),
        copies=result.get("copies", []),
    )

def generate_image(image_bytes: bytes, tone: str, length: str, num_copies: int, model: str) -> AdcopyImageResponse:
    result = image_model.generate_ad_from_image(
        image_bytes=image_bytes,
        tone=tone,
        length=length,
        num_copies=num_copies,
        model=model,
    )
    return AdcopyImageResponse(
        raw_output=result.get("raw_output"),
        copies=result.get("copies", []),
    )
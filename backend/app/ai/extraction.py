from typing import Optional, Literal
from pydantic import BaseModel, Field, ValidationError

class ExtractedIntent(BaseModel):
    intent: Literal['ADD_CUSTOMER','ADD_CREDIT','RECORD_PAYMENT','CHECK_BALANCE','DAILY_SUMMARY','KHATA_SUMMARY','STOCK_SUMMARY','CORRECT_LAST','CLARIFY']
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict = Field(default_factory=dict)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    clarification_options: list[str] = Field(default_factory=list)

CONFIDENCE_THRESHOLD = 0.7

def validate_extraction(raw: dict) -> ExtractedIntent:
    obj = ExtractedIntent(**raw)
    if obj.confidence < CONFIDENCE_THRESHOLD and obj.intent != 'CLARIFY':
        return ExtractedIntent(intent='CLARIFY', confidence=obj.confidence, entities=obj.entities, clarification_needed=True, clarification_question='Could you please repeat that?', clarification_options=[])
    return obj

def parse_llm_json(text: str) -> dict:
    import json
    text = text.strip()
    if text.startswith('`'):
        text = text.strip('').replace('json', '', 1).strip()
    return json.loads(text)

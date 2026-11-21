import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.ai.extraction import ExtractedIntent, validate_extraction, parse_llm_json
from app.ai.llm import extract_intent

def make_llm_response(payload):
    return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(payload)}}]}, request=httpx.Request('POST', 'http://test'))

@pytest.mark.asyncio
async def test_extract_intent_mocked():
    payload = {'intent': 'ADD_CREDIT', 'confidence': 0.95, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 34000, 'date_expr': 'aaj'}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}
    mock_resp = make_llm_response(payload)
    with patch('httpx.AsyncClient.post', new=AsyncMock(return_value=mock_resp)):
        result = await extract_intent('Ramesh ka 340 udhaar')
    assert result.intent == 'ADD_CREDIT'
    assert result.entities['amount_paise'] == 34000

@pytest.mark.asyncio
async def test_low_confidence_becomes_clarify():
    payload = {'intent': 'ADD_CREDIT', 'confidence': 0.5, 'entities': {'customer_name': 'Ramesh', 'amount_paise': 34000}, 'clarification_needed': False, 'clarification_question': None, 'clarification_options': []}
    obj = validate_extraction(payload)
    assert obj.intent == 'CLARIFY'

def test_validate_extraction_invalid_raises():
    with pytest.raises(Exception):
        validate_extraction({'intent': 'BOGUS', 'confidence': 0.9})


import json
import httpx
from app.config import settings
from app.ai.prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES
from app.ai.extraction import parse_llm_json, validate_extraction, ExtractedIntent

async def call_llm(transcript: str) -> dict:
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    for user_msg, expected in FEW_SHOT_EXAMPLES:
        messages.append({'role': 'user', 'content': user_msg})
        messages.append({'role': 'assistant', 'content': __import__('json').dumps(expected)})
    messages.append({'role': 'user', 'content': transcript})
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f'{settings.LLM_BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {settings.LLM_API_KEY}'}, 
            json={'model': settings.LLM_MODEL, 'messages': messages, 'response_format': {'type': 'json_object'}, 'temperature': 0.1},
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        return parse_llm_json(content)

async def extract_intent(transcript: str) -> ExtractedIntent:
    raw = await call_llm(transcript)
    try:
        return validate_extraction(raw)
    except Exception as e:
        # Retry once with error feedback
        retry_transcript = transcript + '  [previous output invalid: ' + str(e) + ']' 
        raw2 = await call_llm(retry_transcript)
        try:
            return validate_extraction(raw2)
        except Exception:
            return ExtractedIntent(intent='CLARIFY', confidence=0.0, entities={}, clarification_needed=True, clarification_question='Could you please repeat that?', clarification_options=[])

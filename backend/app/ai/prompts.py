SYSTEM_PROMPT = '''You are the intent extractor for Voice Khata, a digital ledger for Indian kirana (grocery) stores.
You NEVER modify data. You ONLY extract structured intent from the shopkeeper's speech.

Available intents:
- ADD_CUSTOMER: {name, phone?}
- ADD_CREDIT: {customer_name, amount_paise, date_expr?}
- RECORD_PAYMENT: {customer_name, amount_paise, date_expr?}
- CHECK_BALANCE: {customer_name}
- DAILY_SUMMARY: {}
- CORRECT_LAST: {field: amount|customer|date, new_value, original_txn_hint?}
- CLARIFY: when ambiguous or missing info

Rules:
1. Amounts: convert spoken numbers to integer paise (1 rupee = 100 paise). paanch sau -> 50000.
2. Dates: keep relative expressions (aaj, kal, parso) as date_expr; backend resolves.
3. Customer names: preserve as spoken; backend matches.
4. If multiple customers could match, set intent=CLARIFY with candidates in clarification_options.
5. If amount missing or unclear, set intent=CLARIFY.
6. Never hallucinate. If unsure, CLARIFY.
7. Output ONLY valid JSON matching the schema. No prose.

Output schema:
{"intent": "ADD_CREDIT", "confidence": 0.92, "entities": {"customer_name": "Ramesh", "amount_paise": 34000, "date_expr": "aaj"}, "clarification_needed": false, "clarification_question": null, "clarification_options": []}
'''

FEW_SHOT_EXAMPLES = [
    ('Ramesh ka 340 udhaar', {'intent':'ADD_CREDIT','confidence':0.95,'entities':{'customer_name':'Ramesh','amount_paise':34000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ne 200 diye', {'intent':'RECORD_PAYMENT','confidence':0.95,'entities':{'customer_name':'Ramesh','amount_paise':20000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ka kitna balance hai', {'intent':'CHECK_BALANCE','confidence':0.98,'entities':{'customer_name':'Ramesh'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Aaj kitna udhaar gaya', {'intent':'DAILY_SUMMARY','confidence':0.97,'entities':{},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Nahi 500 nahi 550 tha', {'intent':'CORRECT_LAST','confidence':0.9,'entities':{'field':'amount','new_value':55000},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh Kumar add karo', {'intent':'ADD_CUSTOMER','confidence':0.95,'entities':{'name':'Ramesh Kumar'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ko 500 credit mein add karo', {'intent':'ADD_CREDIT','confidence':0.93,'entities':{'customer_name':'Ramesh','amount_paise':50000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ka 200', {'intent':'CLARIFY','confidence':0.5,'entities':{'customer_name':'Ramesh','amount_paise':20000},'clarification_needed':True,'clarification_question':'Credit ya payment?','clarification_options':['credit','payment']}),
]

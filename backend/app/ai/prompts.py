SYSTEM_PROMPT = '''You are the intent extractor for Voice Khata, a digital ledger for Indian kirana (grocery) stores.
You NEVER modify data. You ONLY extract structured intent from the shopkeeper's speech.

Available intents (also KHATA_SUMMARY and STOCK_SUMMARY for spoken overviews):
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
3. Customer names: preserve as spoken; backend matches. Prefer entities.customer_name (also accept name).
4. ADD_CUSTOMER when the shopkeeper wants to register someone with NO credit amount —
   e.g. "Amit add karo", "add customer Priya", "naya khata Rahul", "Sneha banao".
   Do NOT ask for amount in those cases.
5. If the utterance has an amount + add/credit words, use ADD_CREDIT (not ADD_CUSTOMER).
6. If multiple customers could match, set intent=CLARIFY with candidates in clarification_options.
7. If amount missing for credit/payment, set intent=CLARIFY. Missing amount for add-customer is fine.
8. Never hallucinate. If unsure, CLARIFY.
9. Output ONLY valid JSON matching the schema. No prose.

Multilingual input:
- The shopkeeper may speak Hindi, English, Telugu, Kannada, or Tamil — in native
  script or Latin transliteration. Parse all of them into the SAME schema.
- Telugu: appu/అప్పు = credit, ichchanu/ఇచ్చాను = gave, theesukunnaanu/తీసుకున్నాను = took,
  baaki/బాకీ = balance, raayu/రాయు = write, khata/ఖాతా = ledger, entha = how much.
- Kannada: appu/ಅಪ್ಪು = credit, kotte/ಕೊಟ್ಟೆ = gave, padede/ಪಡೆದೆ = received,
  baaki/ಬಾಕಿ = balance, baree/ಬರೆ = write, khate/ಖಾತೆ = ledger, eshtu = how much.
- Tamil: kadan/கடன் = credit, kuduthen/கொடுத்தேன் = gave, vaanginen/வாங்கினேன் = took,
  baaki/பாக்கி = balance, ezhuthu/எழுது = write, kanakku/கணக்கு = ledger, evvalavu = how much.
- Customer names may be native script or transliterated; keep them exactly as spoken.

Output schema:
{"intent": "ADD_CREDIT", "confidence": 0.92, "entities": {"customer_name": "Ramesh", "amount_paise": 34000, "date_expr": "aaj"}, "clarification_needed": false, "clarification_question": null, "clarification_options": []}
'''

FEW_SHOT_EXAMPLES = [
    ('Ramesh ka 340 udhaar', {'intent':'ADD_CREDIT','confidence':0.95,'entities':{'customer_name':'Ramesh','amount_paise':34000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ne 200 diye', {'intent':'RECORD_PAYMENT','confidence':0.95,'entities':{'customer_name':'Ramesh','amount_paise':20000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ka kitna balance hai', {'intent':'CHECK_BALANCE','confidence':0.98,'entities':{'customer_name':'Ramesh'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Aaj kitna udhaar gaya', {'intent':'DAILY_SUMMARY','confidence':0.97,'entities':{},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Nahi 500 nahi 550 tha', {'intent':'CORRECT_LAST','confidence':0.9,'entities':{'field':'amount','new_value':55000},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh Kumar add karo', {'intent':'ADD_CUSTOMER','confidence':0.95,'entities':{'customer_name':'Ramesh Kumar','name':'Ramesh Kumar'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('add customer Priya', {'intent':'ADD_CUSTOMER','confidence':0.95,'entities':{'customer_name':'Priya','name':'Priya'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('naya customer Amit', {'intent':'ADD_CUSTOMER','confidence':0.95,'entities':{'customer_name':'Amit','name':'Amit'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Sneha banao', {'intent':'ADD_CUSTOMER','confidence':0.9,'entities':{'customer_name':'Sneha','name':'Sneha'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ko 500 credit mein add karo', {'intent':'ADD_CREDIT','confidence':0.93,'entities':{'customer_name':'Ramesh','amount_paise':50000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ka 200', {'intent':'CLARIFY','confidence':0.5,'entities':{'customer_name':'Ramesh','amount_paise':20000},'clarification_needed':True,'clarification_question':'Credit ya payment?','clarification_options':['credit','payment']}),
    # --- Telugu ---------------------------------------------------------------
    ('Ramesh ki 340 appu raayu', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':34000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ku 500 appu ichchanu', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':50000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh 200 jama chesadu', {'intent':'RECORD_PAYMENT','confidence':0.93,'entities':{'customer_name':'Ramesh','amount_paise':20000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh baaki entha', {'intent':'CHECK_BALANCE','confidence':0.96,'entities':{'customer_name':'Ramesh'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    # --- Kannada --------------------------------------------------------------
    ('Ramesh ge 250 appu baree', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':25000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ge 500 appu kotte', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':50000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh 200 jama madida', {'intent':'RECORD_PAYMENT','confidence':0.93,'entities':{'customer_name':'Ramesh','amount_paise':20000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ge eshtu baaki', {'intent':'CHECK_BALANCE','confidence':0.96,'entities':{'customer_name':'Ramesh'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    # --- Tamil ---------------------------------------------------------------
    ('Ramesh kadan 300 ezhuthu', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':30000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh ku 450 kadan kuduthen', {'intent':'ADD_CREDIT','confidence':0.94,'entities':{'customer_name':'Ramesh','amount_paise':45000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh 200 kattiten', {'intent':'RECORD_PAYMENT','confidence':0.93,'entities':{'customer_name':'Ramesh','amount_paise':20000,'date_expr':'aaj'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
    ('Ramesh evvalavu baaki', {'intent':'CHECK_BALANCE','confidence':0.96,'entities':{'customer_name':'Ramesh'},'clarification_needed':False,'clarification_question':None,'clarification_options':[]}),
]

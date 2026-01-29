"""
Team and Agent Information Configuration
"""

TEAM_INFO = {
    "group_batch_order_number": "1_1",  # Update with your actual batch and order number
    "team_name": "Clinical AI Solutions",
    "students": [
        {
            "name": "Yuval Rainis",  
            "email": "yuval.rainis@campus.technion.ac.il"  
        },
        {
            "name": "Uri Shteinberg",
            "email": "ushteinberg@campus.technion.ac.il"
        },
        {
            "name": "Sivan Maspin",
            "email": "sivan4599@campus.technion.ac.il"
        }
    ]
}

AGENT_INFO = {
    "description": "AI-powered clinical triage agent that assists nurses by determining patient urgency levels based on structured vital signs and free-text chief complaints, using rule-based safety checks and retrieval-augmented medical knowledge to produce explainable, clinically grounded triage decisions.",
    "purpose": "To provide rapid, accurate, and explainable triage assessments that help healthcare professionals prioritize patient care based on urgency, combining evidence-based medical knowledge with real-time vital signs analysis.",
    "prompt_template": {
        "template": """Patient Assessment:
Age: {age}
Gender: {gender}
Vital Signs:
  - Blood Pressure: {bp}
  - Heart Rate: {hr}
  - Temperature: {temp}
  - Respiratory Rate: {rr}
  - SpO2: {spo2}
Chief Complaint: {chief_complaint}
Additional Symptoms: {symptoms}
Medical History: {history} (optional)

The agent will analyze this information and provide:
1. Triage level (Critical/Urgent/Standard/Non-Urgent)
2. Safety alerts based on vital signs
3. Differential diagnoses with confidence scores
4. Recommended immediate actions
5. Suggested tests and specialists"""
    },
    "prompt_examples": [
        {
            "prompt": "Patient: 45yo male, BP 180/110, HR 120, temp 101.5F, SpO2 95%, complaining of severe chest pain radiating to left arm, shortness of breath, sweating, nausea. No significant medical history.",
            "full_response": """**TRIAGE LEVEL: CRITICAL (Level 1 - Immediate)**

**Safety Alerts:**
**CRITICAL HYPERTENSION**: Blood pressure 180/110 mmHg (Normal: <120/80)
**TACHYCARDIA**: Heart rate 120 bpm (Normal: 60-100)
**FEVER**: Temperature 101.5°F (Normal: 97-99°F)
**CARDIAC SYMPTOMS**: Chest pain with radiation - immediate cardiac workup required

**Primary Assessment:**
Patient presents with classic symptoms of acute coronary syndrome (ACS). The combination of chest pain radiating to the left arm, shortness of breath, sweating (diaphoresis), and nausea are highly suspicious for myocardial infarction.

**Differential Diagnoses:**
1. **Acute Myocardial Infarction (Heart Attack)** - Confidence: HIGH
   - Crushing chest pain with left arm radiation
   - Associated autonomic symptoms (sweating, nausea)
   - Hypertension and tachycardia
   
2. **Unstable Angina** - Confidence: MODERATE
   - Similar presentation to MI
   - Requires immediate cardiac workup to differentiate
   
3. **Aortic Dissection** - Confidence: MODERATE
   - Severe hypertension is a risk factor
   - Chest pain characteristic
   - Life-threatening - requires urgent imaging

**Immediate Actions Required:**
1. ✓ Activate Code STEMI/Cardiac Emergency protocol
2. ✓ 12-lead ECG within 10 minutes
3. ✓ Establish IV access
4. ✓ Continuous cardiac monitoring
5. ✓ Oxygen therapy (target SpO2 > 94%)
6. ✓ Aspirin 325mg (if not contraindicated)
7. ✓ Nitroglycerin sublingual (if SBP > 90)
8. ✓ Prepare for urgent catheterization lab

**Recommended Tests:**
- Troponin I/T (stat, repeat in 3-6 hours)
- Complete Blood Count (CBC)
- Comprehensive Metabolic Panel (CMP)
- Chest X-ray (portable)
- CT Angiography (if aortic dissection suspected)
- Echocardiogram

**Specialist Consultation:**
- Cardiology (IMMEDIATE)
- Cardiothoracic Surgery (on standby)

**Critical Time Targets:**
- Door-to-ECG: < 10 minutes
- Door-to-Balloon (if STEMI): < 90 minutes""",
            "steps": [
                {
                    "module": "Input Validator",
                    "prompt": {"raw_input": "Patient: 45yo male, BP 180/110, HR 120, temp 101.5F, SpO2 95%, complaining of severe chest pain radiating to left arm, shortness of breath, sweating, nausea. No significant medical history."},
                    "response": {"validated": True, "structured_data": {"age": 45, "gender": "male", "vitals": {"bp_systolic": 180, "bp_diastolic": 110, "heart_rate": 120, "temperature": 101.5, "spo2": 95}, "chief_complaint": "severe chest pain radiating to left arm", "symptoms": ["shortness of breath", "sweating", "nausea"]}}
                },
                {
                    "module": "Safety Checker",
                    "prompt": {"vitals": {"bp_systolic": 180, "bp_diastolic": 110, "heart_rate": 120, "temperature": 101.5, "spo2": 95}},
                    "response": {"alerts": ["Critical hypertension: BP 180/110", "Tachycardia: HR 120", "Fever: 101.5F"], "risk_level": "CRITICAL", "immediate_intervention": True}
                },
                {
                    "module": "Symptom Analyzer",
                    "prompt": {"chief_complaint": "severe chest pain radiating to left arm", "additional_symptoms": ["shortness of breath", "sweating", "nausea"]},
                    "response": {"extracted_symptoms": ["chest pain", "radiation to left arm", "dyspnea", "diaphoresis", "nausea"], "red_flags": ["chest pain with radiation", "cardiac symptoms"], "urgency_indicators": ["classic ACS presentation"]}
                },
                {
                    "module": "Knowledge Retriever",
                    "prompt": {"query": "chest pain radiating to left arm shortness of breath sweating male 45", "context": "emergency triage"},
                    "response": {"top_diagnoses": [{"name": "Acute Myocardial Infarction", "confidence": 0.92}, {"name": "Unstable Angina", "confidence": 0.78}, {"name": "Aortic Dissection", "confidence": 0.65}], "recommended_tests": ["ECG", "Troponin", "CBC", "CMP", "Chest X-ray"], "specialists": ["Cardiology", "Cardiothoracic Surgery"]}
                },
                {
                    "module": "Triage Decision Engine",
                    "prompt": {"safety_alerts": ["Critical hypertension", "Tachycardia", "Fever"], "symptoms": ["chest pain", "radiation to left arm", "dyspnea", "diaphoresis", "nausea"], "differential_diagnoses": [{"name": "Acute Myocardial Infarction", "confidence": 0.92}], "knowledge_base_context": {"immediate_actions": ["ECG", "IV access", "Aspirin"], "time_sensitive": True}},
                    "response": {"triage_level": "CRITICAL", "esi_level": 1, "rationale": "Classic presentation of acute coronary syndrome with vital sign abnormalities indicating immediate life-threatening condition", "confidence": 0.95}
                }
            ]
        },
        {
            "prompt": "Patient: 28yo female, BP 118/75, HR 78, temp 98.6F, SpO2 99%, ankle pain and swelling after twisting it while jogging yesterday. Can bear some weight but limping.",
            "full_response": """**TRIAGE LEVEL: NON-URGENT (Level 5)**

**Safety Alerts:**
✓ All vital signs within normal limits
✓ No immediate life or limb threats identified

**Primary Assessment:**
Patient presents with ankle injury consistent with sprain from sports activity. Vital signs are stable and reassuring. Ability to bear weight suggests less severe injury, though fracture cannot be ruled out without imaging.

**Differential Diagnoses:**
1. **Ankle Sprain (Grade I-II)** - Confidence: HIGH
   - Mechanism of injury consistent
   - Able to bear some weight
   - Typical presentation for sports injury
   
2. **Ankle Fracture** - Confidence: LOW-MODERATE
   - Cannot be excluded without imaging
   - Ottawa Ankle Rules indicate X-ray may be needed
   
3. **Soft Tissue Contusion** - Confidence: MODERATE

**Recommended Actions:**
1. ✓ RICE protocol (Rest, Ice, Compression, Elevation)
2. ✓ Pain management (NSAIDs like ibuprofen if not contraindicated)
3. ✓ X-ray of ankle (AP, lateral, mortise views) per Ottawa rules
4. ✓ Non-weight bearing status until fracture ruled out
5. ✓ Follow-up with orthopedics if fracture confirmed

**Recommended Tests:**
- X-ray ankle (3 views)

**Specialist Consultation:**
- Orthopedics (routine, only if fracture found)
- Sports Medicine (follow-up)

**Expected Wait Time:**
Can safely wait 1-2 hours for evaluation. Not urgent.""",
            "steps": [
                {
                    "module": "Input Validator",
                    "prompt": {"raw_input": "Patient: 28yo female, BP 118/75, HR 78, temp 98.6F, SpO2 99%, ankle pain and swelling after twisting it while jogging yesterday. Can bear some weight but limping."},
                    "response": {"validated": True, "structured_data": {"age": 28, "gender": "female", "vitals": {"bp_systolic": 118, "bp_diastolic": 75, "heart_rate": 78, "temperature": 98.6, "spo2": 99}, "chief_complaint": "ankle pain and swelling", "mechanism": "twisting while jogging", "symptoms": ["pain", "swelling", "limping", "can bear some weight"]}}
                },
                {
                    "module": "Safety Checker",
                    "prompt": {"vitals": {"bp_systolic": 118, "bp_diastolic": 75, "heart_rate": 78, "temperature": 98.6, "spo2": 99}},
                    "response": {"alerts": [], "risk_level": "NORMAL", "immediate_intervention": False, "all_parameters_normal": True}
                },
                {
                    "module": "Symptom Analyzer",
                    "prompt": {"chief_complaint": "ankle pain and swelling", "additional_symptoms": ["limping", "can bear some weight"], "mechanism": "twisting while jogging"},
                    "response": {"extracted_symptoms": ["ankle pain", "swelling", "limited mobility", "post-traumatic"], "red_flags": [], "urgency_indicators": ["stable injury", "able to ambulate"]}
                },
                {
                    "module": "Knowledge Retriever",
                    "prompt": {"query": "ankle sprain swelling pain sports injury twisted", "context": "outpatient orthopedic"},
                    "response": {"top_diagnoses": [{"name": "Ankle Sprain", "confidence": 0.88}, {"name": "Ankle Fracture", "confidence": 0.35}, {"name": "Soft Tissue Injury", "confidence": 0.72}], "recommended_tests": ["X-ray ankle"], "specialists": ["Orthopedics", "Sports Medicine"], "treatment": ["RICE protocol", "NSAIDs", "immobilization"]}
                },
                {
                    "module": "Triage Decision Engine",
                    "prompt": {"safety_alerts": [], "symptoms": ["ankle pain", "swelling", "limited mobility"], "differential_diagnoses": [{"name": "Ankle Sprain", "confidence": 0.88}], "knowledge_base_context": {"immediate_actions": ["RICE protocol"], "time_sensitive": False}},
                    "response": {"triage_level": "NON-URGENT", "esi_level": 5, "rationale": "Stable musculoskeletal injury with normal vital signs, no immediate threats, can be managed in routine clinic setting", "confidence": 0.92}
                }
            ]
        }
    ]
}

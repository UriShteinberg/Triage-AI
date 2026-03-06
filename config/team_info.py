"""
Team and Agent Information Configuration
"""

TEAM_INFO = {
    "group_batch_order_number": "2_1",
    "team_name": "Triage AI",
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
        "template": "Patient Assessment:\nAge: {age}\nGender: {gender}\nVital Signs:\n  - Blood Pressure: {bp}\n  - Heart Rate: {hr}\n  - Temperature: {temp}\n  - Respiratory Rate: {rr}\n  - SpO2: {spo2}\nChief Complaint: {chief_complaint}\nAdditional Symptoms: {symptoms}\nMedical History: {history} (optional)\n\nThe agent will analyze this information and provide:\n1. Triage level (Critical/Urgent/Standard/Non-Urgent)\n2. Safety alerts based on vital signs\n3. Differential diagnoses with confidence scores\n4. Recommended immediate actions\n5. Suggested tests and specialists"
    },
    "prompt_examples": [
        {
            "prompt": "Patient: 45yo male, BP 180/110, HR 120, temp 101.5F, SpO2 95%, complaining of severe chest pain radiating to left arm, shortness of breath, sweating, nausea. No significant medical history.",
            "full_response": "**TRIAGE LEVEL: CRITICAL (Level 1 - Immediate)**\n\n**Safety Alerts:**\n**CRITICAL HYPERTENSION**: Blood pressure 180/110 mmHg (Normal: <120/80)\n**TACHYCARDIA**: Heart rate 120 bpm (Normal: 60-100)\n**FEVER**: Temperature 101.5°F (Normal: 97-99°F)\n**CARDIAC SYMPTOMS**: Chest pain with radiation - immediate cardiac workup required\n\n**Primary Assessment:**\nPatient presents with classic symptoms of acute coronary syndrome (ACS). The combination of chest pain radiating to the left arm, shortness of breath, sweating (diaphoresis), and nausea are highly suspicious for myocardial infarction.\n\n**Differential Diagnoses:**\n1. **Acute Myocardial Infarction (Heart Attack)** - Confidence: HIGH\n   - Crushing chest pain with left arm radiation\n   - Associated autonomic symptoms (sweating, nausea)\n   - Hypertension and tachycardia\n   \n2. **Unstable Angina** - Confidence: MODERATE\n   - Similar presentation to MI\n   - Requires immediate cardiac workup to differentiate\n   \n3. **Aortic Dissection** - Confidence: MODERATE\n   - Severe hypertension is a risk factor\n   - Chest pain characteristic\n   - Life-threatening - requires urgent imaging\n\n**Immediate Actions Required:**\n1. [v] Activate Code STEMI/Cardiac Emergency protocol\n2. [v] 12-lead ECG within 10 minutes\n3. [v] Establish IV access\n4. [v] Continuous cardiac monitoring\n5. [v] Oxygen therapy (target SpO2 > 94%)\n6. [v] Aspirin 325mg (if not contraindicated)\n7. [v] Nitroglycerin sublingual (if SBP > 90)\n8. [v] Prepare for urgent catheterization lab\n\n**Recommended Tests:**\n- Troponin I/T (stat, repeat in 3-6 hours)\n- Complete Blood Count (CBC)\n- Comprehensive Metabolic Panel (CMP)\n- Chest X-ray (portable)\n- CT Angiography (if aortic dissection suspected)\n- Echocardiogram\n\n**Specialist Consultation:**\n- Cardiology (IMMEDIATE)\n- Cardiothoracic Surgery (on standby)\n\n**Critical Time Targets:**\n- Door-to-ECG: < 10 minutes\n- Door-to-Balloon (if STEMI): < 90 minutes",
            "steps": [
                {
                    "module": "Input Validator",
                    "prompt": {
                        "raw_input": "Patient: 45yo male, BP 180/110, HR 120, temp 101.5F, SpO2 95%, complaining of severe chest pain radiating to left arm, shortness of breath, sweating, nausea. No significant medical history."
                    },
                    "response": {
                        "validated": True,
                        "structured_data": {
                            "age": 45,
                            "gender": "male",
                            "vitals": {
                                "bp_systolic": 180,
                                "bp_diastolic": 110,
                                "heart_rate": 120,
                                "temperature": 101.5,
                                "spo2": 95
                            },
                            "chief_complaint": "severe chest pain radiating to left arm",
                            "symptoms": [
                                "shortness of breath",
                                "sweating",
                                "nausea"
                            ]
                        }
                    }
                },
                {
                    "module": "Clinical Rule Engine",
                    "prompt": {
                        "vitals": {
                            "bp_systolic": 180,
                            "bp_diastolic": 110,
                            "heart_rate": 120,
                            "temperature": 101.5,
                            "spo2": 95
                        }
                    },
                    "response": {
                        "alerts": [
                            "Critical hypertension: BP 180/110",
                            "Tachycardia: HR 120",
                            "Fever: 101.5F"
                        ],
                        "risk_level": "CRITICAL",
                        "immediate_intervention": True
                    }
                },
                {
                    "module": "Knowledge Retriever (RAG)",
                    "prompt": {
                        "chief_complaint": "severe chest pain radiating to left arm",
                        "additional_symptoms": [
                            "shortness of breath",
                            "sweating",
                            "nausea"
                        ]
                    },
                    "response": {
                        "extracted_symptoms": [
                            "chest pain",
                            "radiation to left arm",
                            "dyspnea",
                            "diaphoresis",
                            "nausea"
                        ],
                        "red_flags": [
                            "chest pain with radiation",
                            "cardiac symptoms"
                        ],
                        "urgency_indicators": [
                            "classic ACS presentation"
                        ]
                    }
                },
                {
                    "module": "Decision Engine (LLM)",
                    "prompt": {
                        "safety_alerts": [
                            "Critical hypertension",
                            "Tachycardia",
                            "Fever"
                        ],
                        "symptoms": [
                            "chest pain",
                            "radiation to left arm",
                            "dyspnea",
                            "diaphoresis",
                            "nausea"
                        ],
                        "differential_diagnoses": [
                            {
                                "name": "Acute Myocardial Infarction",
                                "confidence": 0.92
                            }
                        ],
                        "knowledge_base_context": {
                            "immediate_actions": [
                                "ECG",
                                "IV access",
                                "Aspirin"
                            ],
                            "time_sensitive": True
                        }
                    },
                    "response": {
                        "triage_level": "CRITICAL",
                        "esi_level": 1,
                        "rationale": "Classic presentation of acute coronary syndrome with vital sign abnormalities indicating immediate life-threatening condition",
                        "confidence": 0.95
                    }
                }
            ]
        },
        {
            "prompt": "Patient: 28yo female, BP 118/75, HR 78, temp 98.6F, SpO2 99%, ankle pain and swelling after twisting it while jogging yesterday. Can bear some weight but limping.",
            "full_response": "**TRIAGE LEVEL: NON-URGENT (Level 5)**\n\n**Safety Alerts:**\n[v] All vital signs within normal limits\n[v] No immediate life or limb threats identified\n\n**Primary Assessment:**\nPatient presents with ankle injury consistent with sprain from sports activity. Vital signs are stable and reassuring. Ability to bear weight suggests less severe injury, though fracture cannot be ruled out without imaging.\n\n**Differential Diagnoses:**\n1. **Ankle Sprain (Grade I-II)** - Confidence: HIGH\n   - Mechanism of injury consistent\n   - Able to bear some weight\n   - Typical presentation for sports injury\n   \n2. **Ankle Fracture** - Confidence: LOW-MODERATE\n   - Cannot be excluded without imaging\n   - Ottawa Ankle Rules indicate X-ray may be needed\n   \n3. **Soft Tissue Contusion** - Confidence: MODERATE\n\n**Recommended Actions:**\n1. [v] RICE protocol (Rest, Ice, Compression, Elevation)\n2. [v] Pain management (NSAIDs like ibuprofen if not contraindicated)\n3. [v] X-ray of ankle (AP, lateral, mortise views) per Ottawa rules\n4. [v] Non-weight bearing status until fracture ruled out\n5. [v] Follow-up with orthopedics if fracture confirmed\n\n**Recommended Tests:**\n- X-ray ankle (3 views)\n\n**Specialist Consultation:**\n- Orthopedics (routine, only if fracture found)\n- Sports Medicine (follow-up)\n\n**Expected Wait Time:**\nCan safely wait 1-2 hours for evaluation. Not urgent.",
            "steps": [
                {
                    "module": "Input Validator",
                    "prompt": {
                        "raw_input": "Patient: 28yo female, BP 118/75, HR 78, temp 98.6F, SpO2 99%, ankle pain and swelling after twisting it while jogging yesterday. Can bear some weight but limping."
                    },
                    "response": {
                        "validated": True,
                        "structured_data": {
                            "age": 28,
                            "gender": "female",
                            "vitals": {
                                "bp_systolic": 118,
                                "bp_diastolic": 75,
                                "heart_rate": 78,
                                "temperature": 98.6,
                                "spo2": 99
                            },
                            "chief_complaint": "ankle pain and swelling",
                            "mechanism": "twisting while jogging",
                            "symptoms": [
                                "pain",
                                "swelling",
                                "limping",
                                "can bear some weight"
                            ]
                        }
                    }
                },
                {
                    "module": "Clinical Rule Engine",
                    "prompt": {
                        "vitals": {
                            "bp_systolic": 118,
                            "bp_diastolic": 75,
                            "heart_rate": 78,
                            "temperature": 98.6,
                            "spo2": 99
                        }
                    },
                    "response": {
                        "alerts": [],
                        "risk_level": "NORMAL",
                        "immediate_intervention": False,
                        "all_parameters_normal": True
                    }
                },
                {
                    "module": "Knowledge Retriever (RAG)",
                    "prompt": {
                        "chief_complaint": "ankle pain and swelling",
                        "additional_symptoms": [
                            "limping",
                            "can bear some weight"
                        ],
                        "mechanism": "twisting while jogging"
                    },
                    "response": {
                        "extracted_symptoms": [
                            "ankle pain",
                            "swelling",
                            "limited mobility",
                            "post-traumatic"
                        ],
                        "red_flags": [],
                        "urgency_indicators": [
                            "stable injury",
                            "able to ambulate"
                        ]
                    }
                },
                {
                    "module": "Decision Engine (LLM)",
                    "prompt": {
                        "safety_alerts": [],
                        "symptoms": [
                            "ankle pain",
                            "swelling",
                            "limited mobility"
                        ],
                        "differential_diagnoses": [
                            {
                                "name": "Ankle Sprain",
                                "confidence": 0.88
                            }
                        ],
                        "knowledge_base_context": {
                            "immediate_actions": [
                                "RICE protocol"
                            ],
                            "time_sensitive": False
                        }
                    },
                    "response": {
                        "triage_level": "NON-URGENT",
                        "esi_level": 5,
                        "rationale": "Stable musculoskeletal injury with normal vital signs, no immediate threats, can be managed in routine clinic setting",
                        "confidence": 0.92
                    }
                }
            ]
        }
    ]
}

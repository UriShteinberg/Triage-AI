"""
Decision Engine Module
Step 4: Decision Fusion - Single LLM call to justify triage decision
"""

import os
from typing import Dict, Any
import requests
import json


class DecisionEngine:
    """
    PRIMARY DIAGNOSTIC ENGINE: LLM analyzes patient presentation and makes KTAS decision.
    Uses medical reasoning with vital signs, symptoms, and knowledge base context.
    Rule engine provides safety floor only (prevents under-triage).
    This is the ONLY stage where LLM is used.
    """
    
    def __init__(self):
        self.api_key = os.getenv('LMMOD_API_KEY', '')
        self.api_url = "https://api.llmod.ai/v1/chat/completions"  # LLMod.ai educator platform
        
        # KTAS (Korean Triage Acuity Scale) / ESI levels
        self.urgency_levels = {
            1: "KTAS 1 (Resuscitation) - Immediate",
            2: "KTAS 2 (Emergent) - Within 15 minutes",
            3: "KTAS 3 (Urgent) - Within 30 minutes",
            4: "KTAS 4 (Less Urgent) - Within 1 hour",
            5: "KTAS 5 (Non-Urgent) - Within 2 hours"
        }
    
    def decide(self, patient_data: Dict[str, Any], rule_result: Dict[str, Any],
               knowledge_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final triage decision with LLM justification.
        
        Args:
            patient_data: Normalized patient data
            rule_result: Results from clinical rule engine
            knowledge_result: Retrieved medical knowledge
            
        Returns:
            {
                "urgency_level": str (KTAS 1-5),
                "justification": str,
                "red_flags": list,
                "recommended_actions": list,
                "confidence": float
            }
        """
        
        # If no LLM, use rule-based decision
        if not self.api_key:
            return self._rule_based_decision(patient_data, rule_result, knowledge_result)
        
        try:
            # Build comprehensive prompt
            prompt = self._build_decision_prompt(patient_data, rule_result, knowledge_result)
            
            # Call LLM
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "RPRTHPB-gpt-5-mini",  # LLMod.ai model name for this assignment
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert emergency physician with extensive clinical experience. Your role is to DIAGNOSE the patient's condition and assign the appropriate KTAS triage level (1-5) based on medical reasoning. You have access to vital signs, chief complaint, and relevant medical knowledge from the database. Use your clinical judgment to determine urgency - you are the primary decision-maker, not just providing justification."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 1,  # GPT-5 models only support temperature=1
                "max_tokens": 800  # Optimized for budget: allows full response without waste
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse LLM response
                return self._parse_llm_response(content, rule_result)
            else:
                print(f"❌ LLM API ERROR - Status {response.status_code}: {response.text[:200]}")
                return self._rule_based_decision(patient_data, rule_result, knowledge_result)
                
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return self._rule_based_decision(patient_data, rule_result, knowledge_result)
    
    def _build_decision_prompt(self, patient_data: Dict, rule_result: Dict, 
                                knowledge_result: Dict) -> str:
        """Build comprehensive prompt for LLM"""
        
        # Extract data
        complaint = patient_data.get('chief_complaint', 'Unknown')
        age = patient_data.get('age', 'Unknown')
        sex = patient_data.get('sex', 'Unknown')
        vitals = patient_data.get('vitals', {})
        
        base_urgency = rule_result.get('base_urgency', 'moderate')
        rule_triggers = rule_result.get('rule_triggers', [])
        critical_flags = rule_result.get('critical_flags', [])
        
        high_risk_dx = knowledge_result.get('high_risk_diagnoses', [])
        
        prompt = f"""CLINICAL CASE FOR TRIAGE:

PATIENT DEMOGRAPHICS:
- Age: {age} years old
- Sex: {sex}

CHIEF COMPLAINT:
{complaint}

VITAL SIGNS:
- SpO2 (Oxygen Saturation): {vitals.get('spo2', 'N/A')}%
- Blood Pressure: {vitals.get('sbp', 'N/A')}/{vitals.get('dbp', 'N/A')} mmHg
- Heart Rate: {vitals.get('hr', 'N/A')} bpm
- Respiratory Rate: {vitals.get('rr', 'N/A')}/min
- Temperature: {vitals.get('temp', 'N/A')}°C
- Pain Scale: {vitals.get('pain', 'N/A')}/10

SAFETY BASELINE (minimum urgency from evidence-based rules): {base_urgency.upper()}
Note: This is a FLOOR - you can assign higher urgency based on clinical judgment.

CLINICAL ALERTS:
"""
        
        for trigger in rule_triggers[:5]:
            prompt += f"- {trigger}\n"
        
        if critical_flags:
            prompt += f"\nCRITICAL FLAGS:\n"
            for flag in critical_flags:
                prompt += f"- ⚠️ {flag}\n"
        
        if high_risk_dx:
            prompt += f"\nPOTENTIAL HIGH-RISK DIAGNOSES (from medical knowledge base):\n"
            for dx in high_risk_dx[:3]:
                life_threat = "🔴 LIFE-THREATENING" if dx.get('life_threatening') else ""
                prompt += f"- {dx.get('name')} {life_threat} (Confidence: {dx.get('confidence', 0):.2f})\n"
        
        prompt += f"""

TASK: Diagnose, assign KTAS (1-5), provide reasoning, identify red flags, recommend actions.

KTAS LEVELS:
1=Resuscitation (immediate, life-threatening)
2=Emergent (<15min, high-risk unstable)
3=Urgent (<30min, potentially serious)
4=Less Urgent (<60min)
5=Non-Urgent (<120min)

CONSTRAINT: KTAS ≥ {base_urgency.upper()} baseline (can upgrade, not downgrade).

Return EXACT JSON:
{{
    "diagnosis": "specific condition(s)",
    "urgency_level": "KTAS X (Description)",
    "justification": "2-3 sentence reasoning",
    "red_flags": ["warning 1", "warning 2"],
    "recommended_actions": ["action 1", "action 2", "action 3"]
}}
"""
        
        return prompt
    
    def _parse_llm_response(self, content: str, rule_result: Dict) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        try:
            # Extract JSON from response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            # Find JSON object
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                content = content[start:end]
            
            result = json.loads(content)
            
            # Extract LLM's diagnosis and KTAS assignment
            diagnosis = result.get('diagnosis', 'Clinical assessment pending')
            urgency_level = result.get('urgency_level', 'KTAS 3')
            ktas_num = int(''.join(filter(str.isdigit, urgency_level)) or '3')
            ktas_num = max(1, min(5, ktas_num))  # Clamp to 1-5
            
            # SAFETY FLOOR: LLM cannot assign LOWER urgency than rule baseline
            # (Higher KTAS number = lower urgency, so ktas_num must be <= rule_score)
            rule_score = rule_result.get('urgency_score', 3)
            original_ktas = ktas_num
            if ktas_num > rule_score:  # LLM trying to downgrade below safety floor
                ktas_num = rule_score
                urgency_level = self.urgency_levels[ktas_num]
                print(f"⚠️ Safety constraint: LLM diagnosed KTAS {original_ktas}, but rule baseline is KTAS {rule_score}. Using KTAS {ktas_num}.")
            
            # Log successful LLM diagnosis
            print(f"✅ LLM DIAGNOSIS: {diagnosis}")
            print(f"✅ LLM KTAS ASSIGNMENT: {self.urgency_levels[ktas_num]}")
            
            return {
                "diagnosis": diagnosis,
                "urgency_level": self.urgency_levels[ktas_num],
                "ktas_number": ktas_num,
                "justification": result.get('justification', ''),
                "red_flags": result.get('red_flags', []),
                "recommended_actions": result.get('recommended_actions', []),
                "confidence": 0.95 if original_ktas == ktas_num else 0.85,  # Lower confidence if safety override
                "llm_diagnosis": True,  # LLM made the primary diagnosis
                "diagnostic_mode": "LLM_PRIMARY",  # Clear indicator: using LLM diagnosis
                "safety_override": original_ktas != ktas_num  # True if rule baseline enforced
            }
            
        except Exception as e:
            print(f"LLM parse error: {e}, using rule-based fallback")
            # Fallback to rule-based
            return self._rule_based_decision({}, rule_result, {})
    
    def _rule_based_decision(self, patient_data: Dict, rule_result: Dict, 
                             knowledge_result: Dict) -> Dict[str, Any]:
        """Fallback rule-based decision when LLM unavailable"""
        
        print("❌ LLM UNAVAILABLE - Using rule-based fallback (no diagnosis provided)")
        
        base_urgency = rule_result.get('base_urgency', 'moderate')
        score = rule_result.get('urgency_score', 3)
        rule_triggers = rule_result.get('rule_triggers', [])
        critical_flags = rule_result.get('critical_flags', [])
        
        # Map to KTAS
        ktas_num = score  # Already 1-5 from rule engine
        ktas_num = max(1, min(5, ktas_num))
        
        # Build justification
        justification = f"⚠️ RULE-BASED MODE (LLM unavailable). Baseline urgency: {base_urgency}. "
        if rule_triggers:
            justification += f"Triggered rules: {', '.join(rule_triggers[:2])}."
        
        # Recommended actions
        actions = []
        if ktas_num <= 2:
            actions.append("Immediate physician evaluation")
            actions.append("Continuous monitoring")
        if critical_flags:
            actions.extend(critical_flags[:2])
        
        return {
            "urgency_level": self.urgency_levels[ktas_num],
            "ktas_number": ktas_num,
            "justification": justification,
            "red_flags": critical_flags,
            "recommended_actions": actions if actions else ["Standard triage protocol"],
            "confidence": 0.75,  # Rule-based
            "diagnostic_mode": "RULE_BASED_FALLBACK",  # Clear indicator: not using LLM
            "llm_diagnosis": False,
            "diagnosis": "N/A - LLM unavailable (rule-based assessment only)"
        }

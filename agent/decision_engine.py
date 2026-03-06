"""
Decision Engine Module
Step 4: Decision Fusion - Single LLM call to justify triage decision
"""

import os
from typing import Dict, Any
import requests
import time
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
        self.request_timeout = 30
        self.max_retries = 2
        self.retry_backoff_seconds = 1
        
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
            if knowledge_result.get('high_risk_diagnoses'):
                print(f"RAG CONTEXT: included {len(knowledge_result.get('high_risk_diagnoses', []))} diagnoses in LLM prompt.")
            else:
                print("RAG CONTEXT: empty (no diagnoses included in LLM prompt).")
            
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
                "reasoning_effort": "low",
                "max_tokens": 1200  # Optimized for budget: allows full response without waste
            }
            
            response = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = requests.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=self.request_timeout
                    )
                    break
                except requests.exceptions.RequestException as e:
                    if attempt >= self.max_retries:
                        raise
                    print(f"[!] LLM request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
            
            if response.status_code == 200:
                result = response.json()

                print("=== FULL LLM JSON (first 1200 chars) ===")
                print(json.dumps(result, ensure_ascii=False)[:1200])
                print("=== END FULL LLM JSON ===")

                self._log_token_usage("main", result)
                content = result['choices'][0]['message']['content']
                print("=== RAW LLM OUTPUT (first 500 chars) ===")
                print(content[:500])
                print("=== END RAW LLM OUTPUT ===")
                
                # Parse LLM response
                return self._parse_llm_response(content, rule_result)
            else:
                print(f"[X] LLM API ERROR - Status {response.status_code}: {response.text[:200]}")
                return self._rule_based_decision(patient_data, rule_result, knowledge_result)
                
        except Exception as e:
            print(f"[X] LLM Error: {e}")
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
        risk_domains = knowledge_result.get('risk_domains', [])

        
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
                prompt += f"- [!] {flag}\n"
        
        if high_risk_dx:
            prompt += f"\nPOTENTIAL HIGH-RISK DIAGNOSES (from medical knowledge base):\n"
            for dx in high_risk_dx[:3]:
                life_threat = "🔴 LIFE-THREATENING" if dx.get('life_threatening') else ""
                prompt += f"- {dx.get('name')} {life_threat} (Confidence: {dx.get('confidence', 0):.2f})\n"
        if risk_domains:
            prompt += "\nRISK DOMAINS IDENTIFIED FROM MEDICAL KNOWLEDGE BASE:\n"
            for domain in risk_domains:
                prompt += f"- {domain.upper()} (consider and rule out if life-threatening)\n"

        prompt += f"""

TASK: Diagnose, assign KTAS (1-5), provide reasoning, identify red flags, recommend actions.
You MUST explicitly consider the identified risk domains in your reasoning and address them in the justification.

KTAS LEVELS:
1=Resuscitation (immediate, life-threatening)
2=Emergent (<15min, high-risk unstable)
3=Urgent (<30min, potentially serious)
4=Less Urgent (<60min)
5=Non-Urgent (<120min)

CONSTRAINT: If baseline is KTAS 1-2, you must use that KTAS. If baseline is KTAS 3-5, you may choose any KTAS based on clinical judgment.

RATIONALE REQUIREMENT:
- In the "justification" field, explicitly state the urgency in text (e.g., "This is emergent; evaluate within 15 minutes (KTAS 2)").
- The urgency text in the justification must match the KTAS level in "urgency_level" (unless rule-based override is applied by the system).

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
            justification = result.get('justification', '')
            # Prefer KTAS inferred from narrative/justification; fallback to urgency_level field
            inferred_ktas = self._infer_ktas_from_text(justification)
            if inferred_ktas:
                ktas_num = inferred_ktas
            else:
                ktas_num = int(''.join(filter(str.isdigit, urgency_level)) or '3')
            ktas_num = max(1, min(5, ktas_num))  # Clamp to 1-5
            
            # SAFETY: Only interfere when rule baseline is KTAS 1-2 (highest emergency)
            rule_score = rule_result.get('urgency_score', 3)
            original_ktas = ktas_num
            if rule_score <= 2:
                ktas_num = rule_score
                urgency_level = self.urgency_levels[ktas_num]
                print(f"[!] Safety constraint: Rule baseline is KTAS {rule_score}. Using KTAS {ktas_num} instead of LLM KTAS {original_ktas}.")
            
            # Log successful LLM diagnosis
            print(f"[OK] LLM DIAGNOSIS: {diagnosis}")
            print(f"[OK] LLM KTAS ASSIGNMENT: {self.urgency_levels[ktas_num]}")
            
            return {
                "diagnosis": diagnosis,
                "urgency_level": self.urgency_levels[ktas_num],
                "ktas_number": ktas_num,
                "justification": justification,
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

    def _infer_ktas_from_text(self, text: str) -> int:
        """Infer KTAS number from narrative text (justification/rationale)."""
        if not text:
            return 0
        t = text.lower()

        # Direct KTAS mention in narrative
        for k in range(1, 6):
            if f"ktas {k}" in t or f"ktas-{k}" in t:
                return k

        # Time-based cues
        time_map = {
            1: ["immediate", "resuscitation", "life-threatening", "now", "minutes to die"],
            2: ["within 15 minutes", "within 15 min", "<15 min", "<15 minutes", "emergent"],
            3: ["within 30 minutes", "within 30 min", "<30 min", "<30 minutes", "urgent"],
            4: ["within 1 hour", "within 60 minutes", "within 60 min", "<60 min", "less urgent"],
            5: ["within 2 hours", "within 120 minutes", "within 120 min", "<120 min", "non-urgent"]
        }
        for k, phrases in time_map.items():
            if any(p in t for p in phrases):
                return k

        return 0
    
    def _rule_based_decision(self, patient_data: Dict, rule_result: Dict, 
                             knowledge_result: Dict) -> Dict[str, Any]:
        """Fallback rule-based decision when LLM unavailable"""
        
        print("[X] LLM UNAVAILABLE - Using rule-based fallback (no diagnosis provided)")
        
        base_urgency = rule_result.get('base_urgency', 'moderate')
        score = rule_result.get('urgency_score', 3)
        rule_triggers = rule_result.get('rule_triggers', [])
        critical_flags = rule_result.get('critical_flags', [])
        
        # Map to KTAS
        ktas_num = score  # Already 1-5 from rule engine
        ktas_num = max(1, min(5, ktas_num))
        
        # Build justification
        justification = f"[!] RULE-BASED MODE (LLM unavailable). Baseline urgency: {base_urgency}. "
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

    def _log_token_usage(self, label: str, result: Dict[str, Any]) -> None:
        """Log token usage and warn if above configured threshold."""
        usage = result.get("usage", {}) if isinstance(result, dict) else {}
        if not usage:
            print(f"LLM token usage [{label}]: unavailable")
            return
        total = usage.get("total_tokens")
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        details = usage.get("completion_tokens_details", {}) or {}
        reasoning_tokens = details.get("reasoning_tokens")
        print(f"LLM token usage [{label}]: total={total} prompt={prompt} completion={completion} reasoning={reasoning_tokens}")
        try:
            max_total = int(os.getenv("LMMOD_MAX_TOTAL_TOKENS", "0"))
        except ValueError:
            max_total = 0
        if max_total and isinstance(total, int) and total > max_total:
            print(f"LLM token usage WARNING [{label}]: total_tokens {total} exceeds LMMOD_MAX_TOTAL_TOKENS={max_total}")




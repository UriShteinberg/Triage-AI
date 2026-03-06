"""
Clinical Rule Engine Module
Step 2: Rule-based urgency assessment using deterministic clinical rules
"""

from typing import Dict, List, Any


class ClinicalRuleEngine:
    """
    Deterministic clinical rule engine for baseline urgency assessment.
    This is the CORE of triage - protects against under-triage.
    """
    
    def __init__(self):
        # Critical thresholds for immediate triage
        self.critical_thresholds = {
            'spo2_critical': 90,  # Severe hypoxemia
            'sbp_critical_low': 90,  # Hypotension
            'sbp_critical_high': 180,  # Hypertensive crisis
            'hr_critical_low': 40,  # Severe bradycardia
            'hr_critical_high': 130,  # Severe tachycardia
            'rr_critical_high': 30,  # Severe tachypnea
            'rr_critical_low': 8,  # Severe bradypnea
            'temp_critical_high': 40.0,  # Hyperthermia (Celsius)
            'temp_critical_low': 35.0,  # Hypothermia
            'pain_critical': 8  # Severe pain
        }
        
        # High-risk complaint keywords
        self.high_risk_complaints = [
            'chest pain', 'chest discomfort', 'crushing', 'pressure in chest',
            'shortness of breath', 'difficulty breathing', 'can\'t breathe', 'sob', 'dyspnea',
            'stroke', 'paralysis', 'weakness one side', 'facial droop', 'slurred speech',
            'seizure', 'convulsion', 'unconscious', 'unresponsive', 'altered mental',
            'severe bleeding', 'hemorrhage', 'massive bleeding', 'blood loss',
            'severe head injury', 'head trauma', 'loss of consciousness',
            'suicide', 'suicidal', 'overdose', 'poisoning',
            'anaphylaxis', 'allergic reaction', 'throat closing', 'severe allergy'
        ]
        
    def assess_urgency(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess baseline urgency using clinical rules (NO LLM).
        
        Args:
            patient_data: Normalized patient data with:
                - chief_complaint: str
                - age: int
                - sex: str
                - vitals: dict
                
        Returns:
            {
                "base_urgency": "immediate" | "high" | "moderate" | "low",
                "rule_triggers": [list of triggered rules],
                "urgency_score": int (1-5),
                "critical_flags": [list of critical findings]
            }
        """
        rule_triggers = []
        critical_flags = []
        urgency_score = 2  # Start at low (2) to allow lower-acuity presentations
        
        chief_complaint = (patient_data.get('chief_complaint', '') or '').lower()
        age = patient_data.get('age')
        vitals = patient_data.get('vitals', {})
        
        # RULE 1 Critical Vital Signs
        vital_rules = self._check_critical_vitals(vitals)
        rule_triggers.extend(vital_rules['triggers'])
        critical_flags.extend(vital_rules['critical'])
        urgency_score = max(urgency_score, vital_rules['score'])
        
        # RULE 2 High-Risk Chief Complaints
        complaint_rules = self._check_high_risk_complaints(chief_complaint)
        rule_triggers.extend(complaint_rules['triggers'])
        critical_flags.extend(complaint_rules['critical'])
        urgency_score = max(urgency_score, complaint_rules['score'])
        
        # RULE 3 Age + Complaint Combinations
        age_rules = self._check_age_risk(age, chief_complaint, vitals)
        rule_triggers.extend(age_rules['triggers'])
        urgency_score = max(urgency_score, age_rules['score'])
        
        # RULE 4 Multiple Abnormal Vitals
        multi_vital_rules = self._check_multiple_abnormals(vitals)
        rule_triggers.extend(multi_vital_rules['triggers'])
        urgency_score = max(urgency_score, multi_vital_rules['score'])
        
        # Map internal score to KTAS urgency level
        # Internal: 5=most urgent -> KTAS: 1=most urgent (flip it)
        if urgency_score >= 5:
            base_urgency = "immediate"  # KTAS 1
            ktas_score = 1
        elif urgency_score == 4:
            base_urgency = "high"  # KTAS 2
            ktas_score = 2
        elif urgency_score == 3:
            base_urgency = "moderate"  # KTAS 3
            ktas_score = 3
        elif urgency_score == 2:
            base_urgency = "low"  # KTAS 4
            ktas_score = 4
        else:
            base_urgency = "minimal"  # KTAS 5
            ktas_score = 5
        
        return {
            "base_urgency": base_urgency,
            "rule_triggers": rule_triggers,
            "urgency_score": ktas_score,  # Return KTAS score (1=critical, 5=non-urgent)
            "critical_flags": critical_flags
        }
    
    def _check_critical_vitals(self, vitals: Dict[str, Any]) -> Dict[str, Any]:
        """Check for critically abnormal vital signs"""
        triggers = []
        critical = []
        score = 2  # Default low
        
        # SpO2 < 90 = IMMEDIATE
        spo2 = vitals.get('spo2')
        if spo2 is not None and spo2 < self.critical_thresholds['spo2_critical']:
            triggers.append(f"Hypoxemia (SpO2: {spo2}%)")
            critical.append("Critical hypoxemia - oxygen needed immediately")
            score = 5
        
        # SBP < 90 = IMMEDIATE
        sbp = vitals.get('sbp')
        if sbp is not None and sbp < self.critical_thresholds['sbp_critical_low']:
            triggers.append(f"Hypotension (SBP: {sbp} mmHg)")
            critical.append("Hypotension - potential shock")
            score = 5
        
        # SBP > 180 = HIGH
        if sbp is not None and sbp > self.critical_thresholds['sbp_critical_high']:
            triggers.append(f"Hypertensive crisis (SBP: {sbp} mmHg)")
            critical.append("Hypertensive emergency - stroke risk")
            score = max(score, 4)
        
        # RR > 30 = HIGH
        rr = vitals.get('rr')
        if rr is not None and rr > self.critical_thresholds['rr_critical_high']:
            triggers.append(f"Tachypnea (RR: {rr}/min)")
            critical.append("Severe tachypnea - respiratory distress")
            score = max(score, 4)
        
        # RR < 8 = IMMEDIATE
        if rr is not None and rr < self.critical_thresholds['rr_critical_low']:
            triggers.append(f"Bradypnea (RR: {rr}/min)")
            critical.append("Respiratory failure - immediate intervention")
            score = 5
        
        # HR extremes
        hr = vitals.get('hr')
        if hr is not None:
            if hr > self.critical_thresholds['hr_critical_high']:
                triggers.append(f"Severe tachycardia (HR: {hr} bpm)")
                score = max(score, 4)
            elif hr < self.critical_thresholds['hr_critical_low']:
                triggers.append(f"Severe bradycardia (HR: {hr} bpm)")
                critical.append("Bradycardia - cardiac monitoring needed")
                score = max(score, 4)
        
        # Temperature extremes
        temp = vitals.get('temp')
        if temp is not None:
            if temp >= self.critical_thresholds['temp_critical_high']:
                triggers.append(f"Hyperthermia (Temp: {temp}°C)")
                score = max(score, 4)
            elif temp <= self.critical_thresholds['temp_critical_low']:
                triggers.append(f"Hypothermia (Temp: {temp}°C)")
                score = max(score, 4)
        
        # Severe pain
        pain = vitals.get('pain')
        if pain is not None and pain >= self.critical_thresholds['pain_critical']:
            triggers.append(f"Severe pain (Pain: {pain}/10)")
            score = max(score, 4)
        
        return {"triggers": triggers, "critical": critical, "score": score}
    
    def _check_high_risk_complaints(self, complaint: str) -> Dict[str, Any]:
        """Check for high-risk chief complaints"""
        triggers = []
        critical = []
        score = 2
        
        def _is_negated(text: str, phrase: str) -> bool:
            # Simple negation handling near the matched phrase
            negators = [
                "no", "denies", "deny", "without", "negative for", "not",
                "no evidence of", "absence of", "no sign of"
            ]
            idx = text.find(phrase)
            if idx < 0:
                return False
            window_start = max(0, idx - 40)
            window = text[window_start:idx].strip()
            return any(window.endswith(neg) or neg in window for neg in negators)

        for high_risk in self.high_risk_complaints:
            if high_risk in complaint:
                # Skip if negated (e.g., "no chest pain")
                if _is_negated(complaint, high_risk):
                    continue
                triggers.append(f"High-risk complaint: {high_risk}")
                
                # Certain complaints are ALWAYS high priority
                if any(keyword in complaint for keyword in [
                    'chest pain', 'shortness of breath', 'stroke', 'seizure', 
                    'unconscious', 'severe bleeding', 'suicide', 'anaphylaxis'
                ]):
                    critical.append(f"Life-threatening complaint: {high_risk}")
                    score = max(score, 4)  # At least HIGH
                else:
                    score = max(score, 3)
                break
        
        return {"triggers": triggers, "critical": critical, "score": score}
    
    def _check_age_risk(self, age: int, complaint: str, vitals: Dict[str, Any]) -> Dict[str, Any]:
        """Check age-related risk factors"""
        triggers = []
        score = 2
        
        if age is None:
            return {"triggers": triggers, "score": score}
        
        # Elderly (>65) with respiratory/cardiac complaints = HIGH
        if age > 65:
            if any(keyword in complaint for keyword in [
                'shortness of breath', 'chest pain', 'chest discomfort', 
                'breathing', 'dyspnea', 'sob'
            ]):
                triggers.append("Elderly patient with respiratory/cardiac complaint")
                score = max(score, 4)
            
            # Elderly with hypoxemia = IMMEDIATE
            if vitals.get('spo2') and vitals['spo2'] < 92:
                triggers.append("Elderly patient with hypoxemia")
                score = 5
        
        # Pediatric (<1 year) always gets higher priority
        if age < 1:
            triggers.append("Infant - heightened priority")
            score = max(score, 4)
        
        # Very young (< 3 months) with fever = IMMEDIATE
        if age < 0.25 and vitals.get('temp') and vitals['temp'] > 38.0:  # 3 months
            triggers.append("Neonate with fever - sepsis risk")
            score = 5
        
        return {"triggers": triggers, "score": score}
    
    def _check_multiple_abnormals(self, vitals: Dict[str, Any]) -> Dict[str, Any]:
        """Check for multiple abnormal vitals (systemic issue)"""
        triggers = []
        score = 2
        abnormal_count = 0
        
        # Count abnormal vitals
        if vitals.get('spo2') and vitals['spo2'] < 95:
            abnormal_count += 1
        if vitals.get('sbp') and (vitals['sbp'] < 100 or vitals['sbp'] > 160):
            abnormal_count += 1
        if vitals.get('hr') and (vitals['hr'] < 60 or vitals['hr'] > 100):
            abnormal_count += 1
        if vitals.get('rr') and (vitals['rr'] < 12 or vitals['rr'] > 20):
            abnormal_count += 1
        if vitals.get('temp') and (vitals['temp'] < 36.0 or vitals['temp'] > 38.0):
            abnormal_count += 1
        
        # 2+ abnormal vitals = systemic issue
        if abnormal_count >= 2:
            triggers.append(f"Multiple abnormal vitals ({abnormal_count} deviations)")
            score = max(score, 4)
        
        # 3+ abnormal = potentially critical
        if abnormal_count >= 3:
            triggers.append("Systemic instability - multiple deranged vitals")
            score = 5
        
        return {"triggers": triggers, "score": score}

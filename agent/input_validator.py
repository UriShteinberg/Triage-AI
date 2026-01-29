"""
Input Validator Module
Step 1: Normalization - Validates and normalizes structured patient data
"""

from typing import Dict, Any


class InputValidator:
    """
    Validates structured patient input and creates unified internal representation.
    Accepts either JSON object or text (backward compatible).
    """
    
    def __init__(self):
        # Valid ranges for validation
        self.valid_ranges = {
            'age': (0, 120),
            'spo2': (0, 100),
            'sbp': (40, 300),
            'dbp': (20, 200),
            'hr': (20, 250),
            'rr': (4, 60),
            'temp': (32, 43),
            'pain': (0, 10)
        }
        
    def validate(self, patient_input: Any) -> Dict[str, Any]:
        """
        Validate and normalize patient input into unified format.
        
        Args:
            patient_input: Either Dict (structured JSON) or str (free text - backward compatible)
            
        Returns:
            Dict with validated flag and normalized patient data:
            {
                "valid": bool,
                "errors": list,
                "normalized_data": {
                    "chief_complaint": str,
                    "age": int,
                    "sex": str,
                    "vitals": {
                        "spo2": int,
                        "sbp": int,
                        "dbp": int,
                        "hr": int,
                        "rr": int,
                        "temp": float,
                        "pain": int,
                        "mental_status": str
                    }
                }
            }
        """
        errors = []
        
        # Handle both structured JSON and text input
        if isinstance(patient_input, dict):
            # Check if it's text mode with "prompt" key
            if 'prompt' in patient_input and isinstance(patient_input['prompt'], str):
                normalized = self._parse_text_input(patient_input['prompt'], errors)
            else:
                # Structured JSON mode
                normalized = self._validate_structured_input(patient_input, errors)
        elif isinstance(patient_input, str):
            # Direct text input (backward compatibility)
            normalized = self._parse_text_input(patient_input, errors)
        else:
            errors.append("Invalid input type. Expected dict or str.")
            return {
                "valid": False,
                "errors": errors,
                "normalized_data": None
            }
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "normalized_data": normalized
        }
    
    def _validate_structured_input(self, data: Dict[str, Any], errors: list) -> Dict[str, Any]:
        """Validate structured JSON input"""
        normalized = {
            "chief_complaint": "",
            "age": None,
            "sex": None,
            "vitals": {}
        }
        
        # Extract chief complaint (required)
        normalized['chief_complaint'] = data.get('chief_complaint', data.get('Chief_complain', ''))
        if not normalized['chief_complaint']:
            errors.append("Chief complaint is required")
        
        # Extract age (optional but validated if present)
        age = data.get('age', data.get('Age'))
        if age is not None:
            try:
                age = int(age)
                if not (self.valid_ranges['age'][0] <= age <= self.valid_ranges['age'][1]):
                    errors.append(f"Age {age} out of valid range")
                normalized['age'] = age
            except (ValueError, TypeError):
                errors.append(f"Invalid age value: {age}")
        
        # Extract sex
        sex = data.get('sex', data.get('Sex'))
        if sex is not None:
            sex_str = str(sex).strip().lower()
            if sex_str in ['m', '1', 'male']:
                normalized['sex'] = 'M'
            elif sex_str in ['f', '2', 'female']:
                normalized['sex'] = 'F'
            else:
                normalized['sex'] = sex_str.upper()[:1] if sex_str else None
        
        # Extract vitals
        vitals_input = data.get('vitals', {})
        if not isinstance(vitals_input, dict):
            # Try to extract from root level (support CSV format)
            vitals_input = {
                'spo2': data.get('Saturation', data.get('spo2')),
                'sbp': data.get('SBP', data.get('sbp')),
                'dbp': data.get('DBP', data.get('dbp')),
                'hr': data.get('HR', data.get('hr')),
                'rr': data.get('RR', data.get('rr')),
                'temp': data.get('BT', data.get('temp')),
                'pain': data.get('NRS_pain', data.get('pain')),
                'mental_status': data.get('Mental', data.get('mental_status'))
            }
        
        # Validate each vital sign
        normalized['vitals'] = self._extract_and_validate_vitals(vitals_input, errors)
        
        return normalized
    
    def _extract_and_validate_vitals(self, vitals: Dict[str, Any], errors: list) -> Dict[str, Any]:
        """Extract and validate vital signs"""
        validated_vitals = {}
        
        vital_mappings = {
            'spo2': ['spo2', 'Saturation', 'oxygen_saturation'],
            'sbp': ['sbp', 'SBP', 'systolic', 'bp_systolic'],
            'dbp': ['dbp', 'DBP', 'diastolic', 'bp_diastolic'],
            'hr': ['hr', 'HR', 'heart_rate', 'pulse'],
            'rr': ['rr', 'RR', 'respiratory_rate', 'resp_rate'],
            'temp': ['temp', 'BT', 'temperature'],
            'pain': ['pain', 'NRS_pain', 'pain_score'],
            'mental_status': ['mental_status', 'Mental', 'GCS', 'consciousness']
        }
        
        for vital_key, possible_keys in vital_mappings.items():
            value = None
            for key in possible_keys:
                if key in vitals and vitals[key] is not None:
                    value = vitals[key]
                    break
            
            if value is not None:
                try:
                    if vital_key == 'mental_status':
                        validated_vitals[vital_key] = str(value)
                    elif vital_key == 'temp':
                        value = float(value)
                        if self.valid_ranges[vital_key][0] <= value <= self.valid_ranges[vital_key][1]:
                            validated_vitals[vital_key] = value
                        else:
                            errors.append(f"Temperature {value} out of valid range")
                    else:
                        value = int(float(value))
                        if vital_key in self.valid_ranges:
                            if self.valid_ranges[vital_key][0] <= value <= self.valid_ranges[vital_key][1]:
                                validated_vitals[vital_key] = value
                            else:
                                errors.append(f"{vital_key.upper()} {value} out of valid range")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {vital_key} value: {value}")
        
        return validated_vitals
    
    def _parse_text_input(self, text: str, errors: list) -> Dict[str, Any]:
        """Parse free-text input (backward compatibility)"""
        import re
        
        normalized = {
            "chief_complaint": text,
            "age": None,
            "sex": None,
            "vitals": {}
        }
        
        # Try to extract vitals from text
        patterns = {
            'age': r'(\d{1,3})\s*(?:yo|y/o|year|yr)',
            'sex': r'\b(male|female|m|f)\b',
            'spo2': r'SpO2:?\s*(\d{2,3})%?',
            'sbp_dbp': r'BP:?\s*(\d{2,3})\s*/\s*(\d{2,3})',
            'hr': r'HR:?\s*(\d{2,3})',
            'rr': r'RR:?\s*(\d{1,2})',
            'temp': r'temp(?:erature)?:?\s*(\d{2,3}(?:\.\d)?)',
            'pain': r'pain:?\s*(\d{1,2})'
        }
        
        # Age
        age_match = re.search(patterns['age'], text, re.IGNORECASE)
        if age_match:
            normalized['age'] = int(age_match.group(1))
        
        # Sex
        sex_match = re.search(patterns['sex'], text, re.IGNORECASE)
        if sex_match:
            s = sex_match.group(1).lower()
            normalized['sex'] = 'M' if s in ['male', 'm'] else 'F'
        
        # Vitals
        spo2_match = re.search(patterns['spo2'], text, re.IGNORECASE)
        if spo2_match:
            normalized['vitals']['spo2'] = int(spo2_match.group(1))
        
        bp_match = re.search(patterns['sbp_dbp'], text, re.IGNORECASE)
        if bp_match:
            normalized['vitals']['sbp'] = int(bp_match.group(1))
            normalized['vitals']['dbp'] = int(bp_match.group(2))
        
        hr_match = re.search(patterns['hr'], text, re.IGNORECASE)
        if hr_match:
            normalized['vitals']['hr'] = int(hr_match.group(1))
        
        rr_match = re.search(patterns['rr'], text, re.IGNORECASE)
        if rr_match:
            normalized['vitals']['rr'] = int(rr_match.group(1))
        
        temp_match = re.search(patterns['temp'], text, re.IGNORECASE)
        if temp_match:
            normalized['vitals']['temp'] = float(temp_match.group(1))
        
        pain_match = re.search(patterns['pain'], text, re.IGNORECASE)
        if pain_match:
            normalized['vitals']['pain'] = int(pain_match.group(1))
        
        return normalized

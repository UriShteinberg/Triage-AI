"""
Knowledge Retriever Module
Step 3: Medical Risk Recall using RAG (Pinecone)
"""

import os
from pathlib import Path
from typing import Dict, List, Any

from dotenv import load_dotenv
from pinecone import Pinecone
import requests
import math

_repo_root = Path(__file__).resolve().parents[1]
_dotenv_path = os.getenv("ENV_FILE", str(_repo_root / ".env"))
load_dotenv(dotenv_path=_dotenv_path, override=True)


class KnowledgeRetriever:
    """
    RAG-based medical knowledge retrieval.
    Recalls life-threatening possibilities - does NOT make decisions.
    """
    def _build_rag_query(self, chief_complaint: str, rule_triggers: list, vitals: dict) -> str:
        parts = []

        # Complaint - preserve critical clinical terms
        if chief_complaint:
            cc = chief_complaint.lower()

            # Remove prefix
            cc = cc.replace("patient:", "").strip()

            # Preserve critical medical terms before cleaning
            critical_terms = {
                'mva': 'motor vehicle accident trauma',
                'gcs': 'glasgow coma scale altered consciousness',
                'trauma': 'traumatic injury',
                'accident': 'trauma injury',
                'hemorrhage': 'bleeding hemorrhage',
                'stroke': 'stroke cerebrovascular',
                'seizure': 'seizure epilepsy',
                'syncope': 'syncope loss consciousness fainting',
                'pregnant': 'pregnancy obstetric',
                'diabetic': 'diabetes mellitus diabetic',
                'chest pain': 'chest pain cardiac coronary',
                'abdominal pain': 'abdominal pain',
                'headache': 'headache cephalalgia',
                'shortness of breath': 'dyspnea respiratory distress breathing difficulty',
                'difficulty breathing': 'dyspnea respiratory distress breathing difficulty'
            }
            
            # Expand critical terms
            for term, expansion in critical_terms.items():
                if term in cc:
                    cc = cc.replace(term, expansion)
            
            # Detect classic clinical syndromes by keyword combinations
            syndrome_patterns = []
            
            # Meningitis/Meningococcemia patterns
            has_fever = any(word in cc for word in ['fever', 'febrile', 'temperature'])
            has_rash = any(word in cc for word in ['rash', 'petechial', 'petechiae', 'purpura', 'purpuric'])
            has_neuro = any(word in cc for word in ['neck stiff', 'stiff neck', 'lethargy', 'lethargic', 'confusion', 'confused', 'altered mental', 'altered consciousness'])
            has_headache = 'headache' in cc or 'cephalalgia' in cc
            
            if has_fever and has_rash and has_neuro:
                syndrome_patterns.append("meningitis meningococcemia bacterial infection sepsis spinal fluid infection")
            elif has_fever and has_neuro and has_headache:
                syndrome_patterns.append("meningitis encephalitis central nervous system infection brain inflammation")
            elif has_fever and has_neuro:
                syndrome_patterns.append("meningitis encephalitis infection")
            elif has_rash and (has_fever or has_neuro):
                syndrome_patterns.append("meningococcemia sepsis bacterial infection")
            
            # Acute coronary syndrome patterns
            has_chest_pain = any(word in cc for word in ['chest pain', 'chest discomfort', 'cardiac'])
            has_cardiac_radiation = any(word in cc for word in ['arm', 'jaw', 'shoulder', 'radiating'])
            has_diaphoresis = any(word in cc for word in ['diaphoresis', 'diaphoretic', 'sweating', 'clammy'])
            
            if has_chest_pain and (has_cardiac_radiation or has_diaphoresis):
                syndrome_patterns.append("acute coronary syndrome myocardial infarction heart attack angina")
            
            # Stroke patterns
            has_weakness = any(word in cc for word in ['weakness', 'weak', 'paralysis', 'hemiparesis'])
            has_speech = any(word in cc for word in ['slurred speech', 'speech difficulty', 'aphasia'])
            has_facial = any(word in cc for word in ['facial droop', 'face droop'])
            
            if (has_weakness or has_speech or has_facial) and 'acute' in cc:
                syndrome_patterns.append("stroke cerebrovascular accident ischemic stroke hemorrhagic stroke")
            
            # Add syndrome patterns to query
            if syndrome_patterns:
                cc = cc + " " + " ".join(syndrome_patterns)

            # Remove numeric vitals (noise for semantic search)
            for token in ["bp", "hr", "rr", "spo2", "temp", "°c", "%", "mmhg", "bpm"]:
                cc = cc.replace(token, " ")

            # Keep only letters and spaces, remove isolated numbers
            cc = "".join(ch if (ch.isalpha() or ch.isspace()) else " " for ch in cc)
            cc = " ".join(cc.split())  # Clean whitespace

            parts.append(cc)


        # Vitals - use explicit clinical descriptions to improve semantic matching
        if isinstance(vitals, dict):
            spo2 = vitals.get("spo2")
            sbp = vitals.get("sbp")
            hr = vitals.get("hr")
            rr = vitals.get("rr")
            temp = vitals.get("temp")

            # Low oxygen - critical hypoxemia
            if spo2 is not None and spo2 <= 92:
                if spo2 < 88:
                    parts.append("critical hypoxemia low oxygen level respiratory failure")
                else:
                    parts.append("hypoxemia decreased oxygen saturation")
            
            # Blood pressure abnormalities
            if sbp is not None:
                if sbp <= 90:
                    if sbp < 80:
                        parts.append("severe hypotension shock low blood pressure circulatory collapse")
                    else:
                        parts.append("hypotension low blood pressure")
                elif sbp >= 180:
                    parts.append("severe hypertension high blood pressure")
            
            # Heart rate
            if hr is not None:
                if hr >= 120:
                    if hr >= 150:
                        parts.append("severe tachycardia rapid heart rate cardiovascular instability")
                    else:
                        parts.append("tachycardia elevated heart rate")
                elif hr <= 50:
                    parts.append("bradycardia slow heart rate")
            
            # Respiratory rate
            if rr is not None and rr >= 24:
                if rr >= 30:
                    parts.append("severe tachypnea respiratory distress")
                else:
                    parts.append("tachypnea increased respiratory rate")
            
            # Temperature
            if temp is not None:
                if temp >= 38.0:
                    if temp >= 39.0:
                        parts.append("high fever severe infection")
                    else:
                        parts.append("fever elevated temperature")
                elif temp <= 35.0:
                    parts.append("hypothermia low temperature")

        # Clean and limit rule triggers (skip redundant ones)
        if rule_triggers:
            for t in rule_triggers[:2]:
                if not t:
                    continue
                clean = str(t).lower()
                # Remove redundant prefixes
                clean = clean.replace("high-risk complaint:", "").strip()
                # Skip if already covered by vital signs description
                if any(word in clean for word in ["hypotension", "tachycardia", "tachypnea", "hypoxemia"]):
                    continue
                parts.append(clean)

        # Build final query
        query = " | ".join(parts)
        return query[:800]  # Increased from 600 to allow richer descriptions

    def __init__(self):
        self.api_key = os.getenv('PINECONE_API_KEY', '')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'triage-knowledge')
        self.index_host = os.getenv('PINECONE_INDEX_HOST', '')
        self.lmmod_api_key = os.getenv('LMMOD_API_KEY', '')
        self.lmmod_url = "https://api.llmod.ai/v1/embeddings"  # LLMod.ai educator platform
        self.debug = os.getenv('RAG_DEBUG', '').strip().lower() in ('1', 'true', 'yes', 'on')
        try:
            self.score_threshold = float(os.getenv('RAG_SCORE_THRESHOLD', '0.55'))
        except ValueError:
            self.score_threshold = 0.55
        try:
            self.debug_top_k = int(os.getenv('RAG_TOP_K', '10'))
        except ValueError:
            self.debug_top_k = 10
        
        self.pc = None
        self.index = None
        
        if self.api_key:
            try:
                self.pc = Pinecone(api_key=self.api_key)
                if self.index_host:
                    self.index = self.pc.Index(self.index_name, host=self.index_host)
                if self.debug and self.index:
                    print(f"RAG DEBUG: index_name='{self.index_name}' host='{self.index_host or 'default'}'")
                    try:
                        stats = self.index.describe_index_stats()
                        print(f"RAG DEBUG: index_stats={stats}")
                    except Exception as e:
                        print(f"RAG DEBUG: describe_index_stats failed: {e}")
            except Exception as e:
                print(f"Pinecone initialization error: {e}")
        elif self.debug:
            print("RAG DEBUG: PINECONE_API_KEY not set; retrieval will use fallback.")
    
    def retrieve(self, patient_data: Dict[str, Any], rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve high-risk diagnoses based on patient presentation.
        Also extract broader risk domains to guide LLM reasoning.
        """
        try:
            # --- Build RAG query safely ---
            complaint = patient_data.get('chief_complaint', '')
            triggers = rule_result.get('rule_triggers', []) or []
            vitals = patient_data.get('vitals', {}) or {}

            query = self._build_rag_query(complaint, triggers, vitals)

            # Age context
            age = patient_data.get('age')
            if age:
                if age > 65:
                    query = (query + " | elderly")[:600]
                elif age < 18:
                    query = (query + " | pediatric")[:600]

            if self.debug:
                print(f"RAG DEBUG: query='{query}'")
                print(f"RAG DEBUG: query_len={len(query)}")

            if not self.index:
                if self.debug:
                    print("RAG DEBUG: Pinecone index not initialized; using fallback knowledge.")
                return self._fallback_knowledge(query, patient_data)

            # --- Get embedding ---
            embedding = self._get_embedding(query)
            if not embedding:
                if self.debug:
                    print("RAG DEBUG: embedding missing; using fallback knowledge.")
                return self._fallback_knowledge(query, patient_data)

            # --- Query Pinecone ---
            results = self.index.query(
                vector=embedding,
                top_k=self.debug_top_k,
                include_metadata=True,
                include_values=self.debug,
                namespace=os.getenv('PINECONE_NAMESPACE', 'ccdx_kb')
            )

            if self.debug:
                matches = results.get('matches', [])
                print(f"RAG DEBUG: matches_found={len(matches)} score_threshold={self.score_threshold}")
                for match in matches:
                    score = match.get('score', 0)
                    meta = match.get('metadata', {})
                    name = meta.get('diagnosis_name', '')
                    print(f"RAG DEBUG: match score={score:.4f} name='{name}'")

            diagnoses = []
            specialists = set()
            tests = set()
            risk_domains = set()
            seen_diagnoses = {}  # Track unique diagnoses by name

            for match in results.get('matches', []):
                metadata = match.get('metadata', {})
                score = match.get('score', 0)
                diagnosis_name = metadata.get('diagnosis_name', '')

                if diagnosis_name and score > self.score_threshold:
                    # Deduplicate: only keep highest scoring instance of each diagnosis
                    if diagnosis_name in seen_diagnoses:
                        if score > seen_diagnoses[diagnosis_name]['confidence']:
                            # Replace with higher score
                            diagnoses.remove(seen_diagnoses[diagnosis_name])
                        else:
                            # Skip this duplicate with lower score
                            continue
                    
                    life_threatening = self._is_life_threatening(diagnosis_name, metadata)

                    diagnosis_entry = {
                        'name': diagnosis_name,
                        'life_threatening': life_threatening,
                        'confidence': float(score),
                        'symptoms': metadata.get('diagnosis_symptoms_text', ''),
                        'recommended_tests': self._extract_tests(metadata)
                    }
                    
                    diagnoses.append(diagnosis_entry)
                    seen_diagnoses[diagnosis_name] = diagnosis_entry

                    # Extract risk domain
                    domain = self._map_to_risk_domain(diagnosis_name)
                    if domain != "other":
                        risk_domains.add(domain)

                    if metadata.get('specialties_list'):
                        specialists.update(self._parse_list(metadata['specialties_list']))
                    if metadata.get('tests_list'):
                        tests.update(self._parse_list(metadata['tests_list']))

            # Sort and limit to top 5 unique diagnoses
            unique_diagnoses = sorted(
                diagnoses,
                key=lambda x: (x['life_threatening'], x['confidence']),
                reverse=True
            )[:5]

            if self.debug:
                print(f"RAG DEBUG: unique_diagnoses={len(unique_diagnoses)} (after deduplication from {len(results.get('matches', []))} matches)")

            return {
                "high_risk_diagnoses": unique_diagnoses,
                "risk_domains": list(risk_domains),
                "recommended_specialists": list(specialists)[:3],
                "recommended_tests": list(tests)[:5]
            }

        except Exception as e:
            print(f"Knowledge retrieval error: {e}")
            return self._fallback_knowledge(patient_data.get('chief_complaint', ''), patient_data)

    
    def _build_focused_query(self, patient_data: Dict[str, Any], rule_result: Dict[str, Any]) -> str:
        """Build focused RAG query from patient data + rule triggers"""
        query_parts = []
        
        # Chief complaint
        complaint = patient_data.get('chief_complaint', '')
        if complaint:
            query_parts.append(complaint)
        
        # Add critical rule triggers
        triggers = rule_result.get('rule_triggers', [])
        if triggers:
            # Extract key terms from triggers
            for trigger in triggers[:2]:  # Top 2 triggers
                query_parts.append(trigger)
        
        # Add age context
        age = patient_data.get('age')
        if age:
            if age > 65:
                query_parts.append("elderly")
            elif age < 18:
                query_parts.append("pediatric")
        
        return " ".join(query_parts)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding vector from LMmod.ai"""
        if not self.lmmod_api_key:
            return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.lmmod_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "RPRTHPB-text-embedding-3-small",  # LLMod.ai model name
                "input": text,
                "dimensions": 1024  # Match Pinecone index dimension
            }
            if self.debug:
                print(f"RAG DEBUG: embedding_model={payload['model']} dims={payload['dimensions']} input_len={len(text)}")
            
            response = requests.post(self.lmmod_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['data'][0]['embedding']
            if self.debug:
                print(f"RAG DEBUG: embedding_status={response.status_code} body_head={response.text[:200]}")
            
        except Exception as e:
            print(f"Embedding error: {e}")
        
        return None
    
    def _is_life_threatening(self, diagnosis_name: str, metadata: Dict) -> bool:
        """Determine if diagnosis is life-threatening"""
        life_threatening_keywords = [
            'embolism', 'infarction', 'stroke', 'aneurysm', 'dissection',
            'sepsis', 'shock', 'cardiac arrest', 'respiratory failure',
            'hemorrhage', 'perforation', 'tamponade', 'pneumothorax',
            'meningitis', 'encephalitis', 'acute coronary', 'myocardial'
        ]
        
        diagnosis_lower = diagnosis_name.lower()
        return any(keyword in diagnosis_lower for keyword in life_threatening_keywords)
    
    def _map_to_risk_domain(self, diagnosis_name: str) -> str:
        """Map diagnosis name to broader risk domain"""
        name = diagnosis_name.lower()

        if any(k in name for k in ["coronary", "myocardial", "cardiac", "infarction"]):
            return "cardiovascular"
        if any(k in name for k in ["embol", "thrombo", "dvt", "pe"]):
            return "thromboembolic"
        if any(k in name for k in ["sepsis", "infection", "meningitis"]):
            return "infectious"
        if any(k in name for k in ["stroke", "aneurysm", "dissection"]):
            return "neurological/vascular"
        if any(k in name for k in ["respiratory failure", "pneumothorax"]):
            return "respiratory"
        
        return "other"

    def _extract_tests(self, metadata: Dict) -> List[str]:
        """Extract recommended tests from metadata"""
        tests = []
        test_list = metadata.get('tests_list', '')
        if test_list:
            tests = self._parse_list(test_list)[:3]  # Top 3 tests
        return tests
    
    def _parse_list(self, value: Any) -> List[str]:
        """Parse comma-separated string or list"""
        if isinstance(value, list):
            return [str(v).strip() for v in value if v]
        elif isinstance(value, str):
            return [v.strip() for v in value.split(',') if v.strip()]
        return []
    
    def _fallback_knowledge(self, query: str, patient_data: Dict) -> Dict[str, Any]:
        """Fallback when Pinecone unavailable"""
        # Rule-based fallback for common presentations
        complaint = query.lower()
        
        diagnoses = []
        if 'chest pain' in complaint or 'chest discomfort' in complaint:
            diagnoses.append({
                'name': 'Acute Coronary Syndrome',
                'life_threatening': True,
                'confidence': 0.75,
                'symptoms': 'Chest pain, pressure, radiating pain',
                'recommended_tests': ['ECG', 'Troponin', 'Chest X-ray']
            })
        
        if 'shortness of breath' in complaint or 'breathing' in complaint:
            diagnoses.append({
                'name': 'Pulmonary Embolism',
                'life_threatening': True,
                'confidence': 0.70,
                'symptoms': 'Shortness of breath, chest pain, hypoxemia',
                'recommended_tests': ['D-Dimer', 'CT Angiography', 'Chest X-ray']
            })
        
        return {
            "high_risk_diagnoses": diagnoses,
            "recommended_specialists": ['Emergency Medicine', 'Cardiology'],
            "recommended_tests": ['ECG', 'Chest X-ray', 'Complete Blood Count']
        }

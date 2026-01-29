"""
Knowledge Retriever Module
Step 3: Medical Risk Recall using RAG (Pinecone)
"""

import os
from typing import Dict, List, Any
from pinecone import Pinecone
import requests


class KnowledgeRetriever:
    """
    RAG-based medical knowledge retrieval.
    Recalls life-threatening possibilities - does NOT make decisions.
    """
    
    def __init__(self):
        self.api_key = os.getenv('PINECONE_API_KEY', '')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'triage-knowledge')
        self.index_host = os.getenv('PINECONE_INDEX_HOST', '')
        self.lmmod_api_key = os.getenv('LMMOD_API_KEY', '')
        self.lmmod_url = "https://api.llmod.ai/v1/embeddings"  # LLMod.ai educator platform
        
        self.pc = None
        self.index = None
        
        if self.api_key:
            try:
                self.pc = Pinecone(api_key=self.api_key)
                if self.index_host:
                    self.index = self.pc.Index(self.index_name, host=self.index_host)
            except Exception as e:
                print(f"Pinecone initialization error: {e}")
    
    def retrieve(self, patient_data: Dict[str, Any], rule_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve high-risk diagnoses based on patient presentation.
        
        Args:
            patient_data: Normalized patient data
            rule_result: Results from clinical rule engine
            
        Returns:
            {
                "high_risk_diagnoses": [
                    {
                        "name": str,
                        "life_threatening": bool,
                        "confidence": float,
                        "symptoms": str,
                        "recommended_tests": list
                    }
                ],
                "recommended_specialists": list,
                "recommended_tests": list
            }
        """
        try:
            # Build focused query from chief complaint + critical findings
            query = self._build_focused_query(patient_data, rule_result)
            
            if not self.index:
                return self._fallback_knowledge(query, patient_data)
            
            # Get embedding
            embedding = self._get_embedding(query)
            if not embedding:
                return self._fallback_knowledge(query, patient_data)
            
            # Query Pinecone for top-K matches
            results = self.index.query(
                vector=embedding,
                top_k=3,  # Optimized: 3 most relevant diagnoses (budget constraint)
                include_metadata=True,
                namespace=os.getenv('PINECONE_NAMESPACE', 'ccdx_kb')
            )
            
            # Extract high-risk diagnoses
            diagnoses = []
            specialists = set()
            tests = set()
            
            for match in results.get('matches', []):
                metadata = match.get('metadata', {})
                score = match.get('score', 0)
                
                diagnosis_name = metadata.get('diagnosis_name', '')
                if diagnosis_name and score > 0.7:  # Only high-confidence matches
                    # Determine if life-threatening
                    life_threatening = self._is_life_threatening(diagnosis_name, metadata)
                    
                    diagnoses.append({
                        'name': diagnosis_name,
                        'life_threatening': life_threatening,
                        'confidence': float(score),
                        'symptoms': metadata.get('diagnosis_symptoms_text', ''),
                        'recommended_tests': self._extract_tests(metadata)
                    })
                    
                    # Collect specialists and tests
                    if metadata.get('specialties_list'):
                        specialists.update(self._parse_list(metadata['specialties_list']))
                    if metadata.get('tests_list'):
                        tests.update(self._parse_list(metadata['tests_list']))
            
            return {
                "high_risk_diagnoses": sorted(diagnoses, key=lambda x: (x['life_threatening'], x['confidence']), reverse=True),
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
            
            response = requests.post(self.lmmod_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['data'][0]['embedding']
            
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

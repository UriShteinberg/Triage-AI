"""
Triage Orchestrator
Step 5: Orchestrates the complete 5-step triage workflow
"""

from typing import Dict, Any
from agent.input_validator import InputValidator
from agent.safety_checker import ClinicalRuleEngine
from agent.knowledge_retriever import KnowledgeRetriever
from agent.decision_engine import DecisionEngine


class TriageOrchestrator:
    """
    Main orchestrator implementing the 5-step triage workflow:
    1. Normalization (Input Validator)
    2. Rule Engine (Clinical Rules)
    3. Medical Risk Recall (RAG/Pinecone)
    4. Decision Fusion (Single LLM Call)
    5. Output Formatting
    """
    
    def __init__(self):
        self.input_validator = InputValidator()
        self.rule_engine = ClinicalRuleEngine()
        self.knowledge_retriever = KnowledgeRetriever()
        self.decision_engine = DecisionEngine()
        
    def execute(self, patient_input: Any) -> Dict[str, Any]:
        """
        Execute complete triage workflow.
        
        Args:
            patient_input: Either structured JSON or free text
            
        Returns:
            {
                "response": str (nurse-friendly output),
                "steps": list (execution trace),
                "metadata": dict
            }
        """
        steps = []
        
        try:
            # STEP 1: Normalization
            validation_result = self.input_validator.validate(patient_input)
            steps.append({
                "step": "1. Normalization",
                "module": "Input Validator",
                "input": self._safe_input_display(patient_input),
                "output": validation_result
            })
            
            if not validation_result.get('valid'):
                return self._format_error_response(
                    "Input validation failed",
                    validation_result.get('errors', []),
                    steps
                )
            
            normalized_data = validation_result['normalized_data']
            
            # STEP 2: Clinical Rule Engine
            rule_result = self.rule_engine.assess_urgency(normalized_data)
            steps.append({
                "step": "2. Rule Engine",
                "module": "Clinical Rule Engine",
                "input": {
                    "vitals": normalized_data.get('vitals', {}),
                    "age": normalized_data.get('age'),
                    "complaint": normalized_data.get('chief_complaint')
                },
                "output": rule_result
            })
            
            # STEP 3: Medical Risk Recall (RAG)
            knowledge_result = self.knowledge_retriever.retrieve(normalized_data, rule_result)
            steps.append({
                "step": "3. Medical Risk Recall",
                "module": "Knowledge Retriever (RAG)",
                "input": {
                    "chief_complaint": normalized_data.get('chief_complaint'),
                    "rule_triggers": rule_result.get('rule_triggers', [])
                },
                "output": knowledge_result
            })
            
            # STEP 4: Decision Fusion (LLM)
            final_decision = self.decision_engine.decide(
                normalized_data,
                rule_result,
                knowledge_result
            )
            steps.append({
                "step": "4. Decision Fusion",
                "module": "Decision Engine (LLM)",
                "input": {
                    "patient_data": normalized_data,
                    "base_urgency": rule_result.get('base_urgency'),
                    "high_risk_diagnoses": [dx.get('name') for dx in knowledge_result.get('high_risk_diagnoses', [])[:3]]
                },
                "output": final_decision
            })
            
            # STEP 5: Format Output
            formatted_response = self._format_nurse_output(
                normalized_data,
                rule_result,
                knowledge_result,
                final_decision
            )
            
            return {
                "response": formatted_response,
                "steps": steps,
                "metadata": {
                    "ktas_level": final_decision.get('ktas_number'),
                    "urgency": final_decision.get('urgency_level'),
                    "confidence": final_decision.get('confidence')
                }
            }
            
        except Exception as e:
            return self._format_error_response(
                f"Triage execution error: {str(e)}",
                [],
                steps
            )
    
    def _format_nurse_output(self, patient_data: Dict, rule_result: Dict,
                             knowledge_result: Dict, decision: Dict) -> str:
        """Format clear, actionable output for nurses"""
        
        output = []
        
        # Header with urgency
        urgency_level = decision.get('urgency_level', 'KTAS 3')
        ktas_num = decision.get('ktas_number', 3)
        
        if ktas_num == 1:
            emoji = "🔴"
        elif ktas_num == 2:
            emoji = "🟠"
        elif ktas_num == 3:
            emoji = "🟡"
        else:
            emoji = "🟢"
        
        output.append(f"{emoji} **TRIAGE DECISION: {urgency_level}**\n")
        
        # Diagnosis (if LLM provided one)
        diagnosis = decision.get('diagnosis')
        if diagnosis:
            output.append(f"**🩺 Diagnosis:** {diagnosis}\n")
        
        # Patient summary
        age = patient_data.get('age', 'Unknown')
        sex = patient_data.get('sex', 'Unknown')
        complaint = patient_data.get('chief_complaint', 'Unknown')
        output.append(f"**Patient:** {age}yo {sex}, Chief Complaint: {complaint}\n")
        
        # Justification
        justification = decision.get('justification', '')
        if justification:
            output.append(f"**Rationale:** {justification}\n")
        
        # Red flags (if any)
        red_flags = decision.get('red_flags', [])
        if red_flags:
            output.append("\n**⚠️ RED FLAGS:**")
            for flag in red_flags[:3]:
                output.append(f"  • {flag}")
            output.append("")
        
        # Recommended actions
        actions = decision.get('recommended_actions', [])
        if actions:
            output.append("**📋 RECOMMENDED ACTIONS:**")
            for action in actions[:4]:
                output.append(f"  • {action}")
            output.append("")
        
        # High-risk diagnoses to consider
        high_risk_dx = knowledge_result.get('high_risk_diagnoses', [])
        if high_risk_dx:
            output.append("**🩺 CONSIDER:**")
            for dx in high_risk_dx[:3]:
                life_threat = " 🔴" if dx.get('life_threatening') else ""
                output.append(f"  • {dx.get('name')}{life_threat}")
            output.append("")
        
        # Recommended tests
        tests = knowledge_result.get('recommended_tests', [])
        if tests:
            output.append(f"**🔬 Tests:** {', '.join(tests[:4])}\n")
        
        return "\n".join(output)
    
    def _format_error_response(self, error_message: str, errors: list, steps: list) -> Dict:
        """Format error response"""
        error_details = "\n".join([f"  • {err}" for err in errors]) if errors else ""
        
        response = f"❌ **Error:** {error_message}"
        if error_details:
            response += f"\n\n**Details:**\n{error_details}"
        
        return {
            "response": response,
            "steps": steps,
            "metadata": {"error": True}
        }
    
    def _safe_input_display(self, patient_input: Any) -> Any:
        """Safe display of input for logging"""
        if isinstance(patient_input, dict):
            return {k: v for k, v in patient_input.items() if k != 'raw_password'}
        return str(patient_input)[:200]  # Limit length

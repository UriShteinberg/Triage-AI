# Clinical Triage Agent Project

## Team Information
- **Team Name**: Clinical AI Solutions
- **Batch**: 1
- **Order**: 1

## Project Description
AI-powered clinical triage agent that assists nurses by determining patient urgency levels based on structured vital signs and free-text chief complaints, using rule-based safety checks and retrieval-augmented medical knowledge to produce explainable, clinically grounded triage decisions.

## Features
- **Rule-Based Safety Module**: Checks vital signs against medical thresholds
- **Symptom Analyzer**: Extracts and validates symptoms from text
- **Medical Knowledge Retrieval**: RAG-based diagnosis and treatment suggestions
- **Triage Decision Engine**: Assigns urgency levels (Critical, Urgent, Standard, Non-Urgent)
- **Explainable Outputs**: Provides reasoning for all decisions

## Architecture
The agent consists of 5 main modules:
1. **Input Validator**: Validates and structures patient data
2. **Safety Checker**: Rule-based vital signs assessment
3. **Symptom Analyzer**: NLP-based symptom extraction
4. **Knowledge Retriever**: Vector search for medical information
5. **Triage Decision Engine**: Combines all signals for final decision

## API Endpoints
- `GET /api/team_info` - Team and student information
- `GET /api/agent_info` - Agent metadata and usage examples
- `GET /api/model_architecture` - Architecture diagram (PNG)
- `POST /api/execute` - Execute triage agent

## Installation

### Prerequisites
- Python 3.9+
- Pinecone account
- Supabase account (optional)
- LLMod.ai API key

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run locally
python app.py
```

## Environment Variables
```
LMMOD_API_KEY=your_lmmod_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=triage-knowledge
PINECONE_INDEX_HOST=your_index_host
PORT=5000
```

## Usage Example

### Request
```json
{
  "prompt": "Patient: 45yo male, BP 180/110, HR 120, temp 101.5F, complaining of severe chest pain radiating to left arm, shortness of breath, nausea"
}
```

### Response
```json
{
  "status": "ok",
  "error": null,
  "response": "**TRIAGE LEVEL: CRITICAL (Level 1)**\n\n**Safety Alerts**:\n- Critical hypertension detected (BP 180/110)\n- Tachycardia (HR 120)\n- Fever present\n\n**Assessment**: Symptoms suggest acute coronary syndrome. Immediate medical intervention required.\n\n**Recommended Actions**:\n1. Activate emergency response\n2. ECG immediately\n3. Cardiac monitoring\n4. IV access\n5. Oxygen if SpO2 < 94%\n\n**Differential Diagnoses**: Myocardial infarction, unstable angina, aortic dissection",
  "steps": [...]
}
```

## Deployment
Deployed on Render: [Your Render URL]

## Development Team
[Team member details from TEAM_INFO]

## License
Academic Project - 2026

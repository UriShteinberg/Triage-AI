# Triage Knowledge Base Tables (Generated from `triage dataset/` CSVs)

This document describes the SQL-generated tables we use as **structured knowledge sources** for a triage agent (RAG / reasoning / suggested checks).

> Note: These tables are **not patient encounter logs** (no vitals, arrival timestamps, staffing, etc.).  
> They represent a **clinical knowledge base**: complaints, candidate diagnoses, and recommended workup/treatment resources.

---

## 1) `chief_complaint_features`

**Title:** Chief Complaint Feature Summary (Body areas • Symptoms • Differential Dx)  
**Grain / Key:** 1 row per `chief_complaint_id`  
**Purpose:** Compact summary of what is associated with a chief complaint.

### Schema
- `chief_complaint_id` (int) — Chief complaint identifier
- `n_body_areas` (int) — Count of distinct body areas linked to the complaint
- `body_areas_list` (text) — Comma-separated body area names
- `n_symptoms` (int) — Count of distinct symptoms linked to the complaint
- `symptoms_list` (text) — Comma-separated symptom names
- `n_diff_dx` (int) — Count of distinct differential diagnoses linked to the complaint
- `diff_dx_list` (text) — Comma-separated diagnosis names (differentials)

**Good for:** quick complaint context, high-level retrieval for a complaint.

---

## 2) `diagnosis_features`

**Title:** Diagnosis Action & Resource Summary (Meds • Tests • Specialties • Procedures)  
**Grain / Key:** 1 row per `diagnosis_id`  
**Purpose:** Action-oriented summary of what’s commonly ordered/used for a diagnosis.

### Schema
- `diagnosis_id` (int) — Diagnosis identifier
- `diagnosis_name` (text) — Diagnosis name
- `n_meds` (int) — Number of medications associated with the diagnosis
- `meds_list` (text) — Comma-separated medication names
- `n_tests` (int) — Number of tests associated with the diagnosis
- `tests_list` (text) — Comma-separated test names
- `n_specialties` (int) — Number of specialties associated with the diagnosis
- `specialties_list` (text) — Comma-separated specialty names
- `n_procedures` (int) — Number of procedures reachable via specialty→procedure mapping
- `procedures_list` (text) — Comma-separated procedure names

**Good for:** “what should we check/order?” explanations; RAG diagnosis cards.

---

## 3) `chief_complaint_knowledge`

**Title:** Chief Complaint Knowledge Pack (Differentials + Suggested Workup Resources)  
**Grain / Key:** 1 row per `chief_complaint_id`  
**Purpose:** Complaint-level summary + aggregated “what to do next” (resources aggregated across its differential diagnoses).

### Schema
- `chief_complaint_id` (int)
- `n_body_areas` (int)
- `body_areas_list` (text)
- `n_symptoms` (int)
- `symptoms_list` (text)
- `n_diff_dx` (int)
- `diff_dx_list` (text)
- `n_meds` (int) — Medications aggregated across the complaint’s differential diagnoses
- `meds_list` (text)
- `n_tests` (int) — Tests aggregated across the complaint’s differential diagnoses
- `tests_list` (text)
- `n_specialties` (int) — Specialties aggregated across the complaint’s differential diagnoses
- `specialties_list` (text)
- `n_procedures` (int) — Procedures aggregated across the complaint’s differential diagnoses
- `procedures_list` (text)

**Good for:** “complaint → what to consider checking” at a high level.

---

## 4) `cc_dx_knowledge` (recommended main table)

**Title:** Chief Complaint → Diagnosis Candidate Knowledge (Explainable + Actionable)  
**Grain / Key:** 1 row per (chief complaint, diagnosis) link — from `differential_diagnoses`  
**Primary Key:** `cc_dx_id`  
**Purpose:** The most useful table for a triage agent: it represents the candidate-diagnosis space and carries the text needed to justify and propose checks.

### Schema
**Link + complaint metadata**
- `cc_dx_id` (int) — Unique id for the link record
- `chief_complaint_id` (int)
- `chief_complaint_name` (text) — Human label (if available from your mapping/table)
- `reason_code` (int) — Code for complaint category/reason (if present)
- `cc_life_threatening` (int/bool) — Complaint flagged as life-threatening
- `cc_msp_enabled` (int/bool) — Feature flag from source KB (if present)
- `cc_diagnosis_count` (int) — Count of diagnoses linked to complaint (if present)

**Differential ranking / flags**
- `diagnosis_id` (int)
- `most_common` (int/bool) — Candidate is “most common”
- `common_peds` (int/bool) — Common in pediatrics
- `life_or_limb_threatening` (int/bool) — Candidate is life/limb threatening

**Diagnosis explainability text**
- `diagnosis_name` (text)
- `diagnosis_description` (text)
- `diagnosis_symptoms_text` (text) — Symptoms narrative
- `diagnosis_workup` (text) — Workup narrative
- `diagnosis_treatment` (text) — Treatment narrative
- `diagnosis_other_specific_tests` (text) — Extra test notes (if present)

**Action/resource aggregations (by diagnosis)**
- `n_meds` (int)
- `meds_list` (text)
- `n_tests` (int)
- `tests_list` (text)
- `n_specialties` (int)
- `specialties_list` (text)
- `n_procedures` (int)
- `procedures_list` (text)

**Good for:** RAG chunks like “Given complaint X, candidate dx Y is common/threatening; here’s workup and suggested tests/meds.”

---

# Optional “Detail” Tables (Extras)

These are **reference/detail** tables that are useful if your agent needs to explain meds/tests/procedures in depth (not just list them).

---

## 5) `medication_details`

**Title:** Medication Reference Details (side effects, precautions, why/how)  
**Grain / Key:** 1 row per `medication_id`  
**Purpose:** Provide deep medication explanations: side effects, precautions, overdose, etc.

### Schema
- `medication_id` (int)
- `medication_name` (text)
- `group_name` (text)
- `prescription` (int/bool)
- `why` (text)
- `how` (text)
- `side_effects` (text)
- `precautions` (text)
- `overdose` (text)
- `special_dietary` (text)
- `storage_conditions` (text)
- `other_information` (text)
- `if_i_forget` (text)
- `combination` (int/bool)
- `generic_medication_id` (int/bool)

**Use when:** your agent outputs medication education or safety warnings.

---

## 6) `procedure_details`

**Title:** Procedure Reference Details (description + complications)  
**Grain / Key:** 1 row per `procedure_id`  
**Purpose:** Explain what a procedure is and common complications.

### Schema
- `procedure_id` (int)
- `procedure_name` (text)
- `procedure_description` (text)
- `common_complications` (text)

**Use when:** your agent discusses procedures beyond simply naming them.

---

## 7) `medical_test_details`

**Title:** Medical Test Reference Details  
**Grain / Key:** 1 row per `medical_test_id`  
**Purpose:** Explain tests: what they are and (sometimes) why they’re ordered.

### Schema
- `medical_test_id` (int)
- `medical_test_name` (text)
- `medical_test_description` (text)

**Use when:** your agent must explain tests (e.g., “why order lactate?”).

---

## 8) `specialty_details`

**Title:** Medical Specialty Reference Details  
**Grain / Key:** 1 row per `medical_specialty_id`  
**Purpose:** Explain referral/specialty routing.

### Schema
- `medical_specialty_id` (int)
- `specialty_name` (text)
- `specialty_description` (text)

**Use when:** your agent recommends consults and you want richer descriptions.

---

## 9) `wise_content_kb`

**Title:** Narrative Guidance Snippets (Wise Content Knowledge Base)  
**Grain / Key:** 1 row per `wise_content_id`  
**Purpose:** Free-text content blocks (guidance, notes, citations) — very RAG-friendly.

### Schema
- `wise_content_id` (int)
- `wiseable_type` (text)
- `wiseable_id` (int)
- `content` (text)
- `attribution_text` (text)
- `medical_society_id` (int)
- `pdf_url` (text)

**Use when:** you want retrieval over authoritative/narrative guidance snippets.

---

## 10) `content_review_audit` (optional)

**Title:** Content Review Audit Trail  
**Grain / Key:** 1 row per `content_review_id`  
**Purpose:** Provenance / reviewer metadata for content fields.

### Schema
- `content_review_id` (int)
- `content_reviewable_type` (text)
- `content_reviewable_id` (int)
- `content_field` (text)
- `content_reviewer_id` (int)
- `reviewer_name` (text)
- `reviewer_attribution_text` (text)
- `reviewer_created_at` (text)
- `reviewer_updated_at` (text)

**Use when:** you care about traceability/QA, usually not needed for triage reasoning.

---

# External Patient-Level Data Sources (Provided CSVs)

These are **patient/encounter-style** tables (the “fact tables”) you use for training/evaluation and for case-based retrieval (similar-patient RAG).

---

## 11) `emergency_service_triage_application` (external)

**File:** `emeregency_service_triage_application.csv`  
**Title:** Emergency Service Triage Application (KTAS-style patient triage rows)  
**Grain / Key:** 1 row per patient visit/record (no explicit `patient_id` column)  
**Purpose:** Real patient-level triage signals: demographics, complaint, vitals, nurse/expert KTAS labels, LOS.

### Schema (as provided)
- `Group`
- `Sex`
- `Age`
- `Patients number per hour`
- `Arrival mode`
- `Injury`
- `Chief_complain`
- `Mental`
- `Pain`
- `NRS_pain`
- `SBP`
- `DBP`
- `HR`
- `RR`
- `BT`
- `Saturation`
- `KTAS_RN`
- `Diagnosis in ED`
- `Disposition`
- `KTAS_expert`
- `Error_group`
- `Length of stay_min`
- `KTAS duration_min`
- `mistriage`

**How it connects to the KB:** join/retrieve by `Diagnosis in ED` ↔ `diagnosis_translations.name` (string match / normalization), and/or use `Chief_complain` as the query text to retrieve `cc_dx_knowledge`.

---

## 12) `sample_hybrid_triage_dataset` (external)

**File:** `sample_hybrid_triage_dataset.csv`  
**Title:** Hybrid Triage Dataset (clinical + operational + clinician decision fields)  
**Grain / Key:** 1 row per patient (`patient_id`)  
**Purpose:** A richer “agent-style” dataset that includes vitals + resource constraints + clinician workflow/override signals.

### Schema (as provided)
- `patient_id`
- `age`
- `sex`
- `symptom_primary`
- `hr`
- `rr`
- `spo2`
- `sbp`
- `temp_c`
- `gcs`
- `comorb_count`
- `poc_lactate`
- `time_since_arrival_min`
- `beds_free`
- `o2_cylinders_free`
- `staff_on_shift`
- `patients_waiting`
- `time_of_day`
- `clinician_exp_yrs`
- `clinician_workload`
- `self_confidence`
- `workload_index`
- `news_like_score`
- `risk_deterioration_prob`
- `resource_need`
- `triage_label`
- `optimizer_action`
- `confidence_band`
- `bias_alert`
- `time_to_decision_sec`
- `clinician_override`

**How it connects to the KB:** use `symptom_primary` + vitals to retrieve relevant `cc_dx_knowledge` and diagnosis/test/medication details. If `symptom_primary` is free text, it works well as a RAG query; if it’s coded, you’ll map it to a complaint/diagnosis vocabulary.

---

# Recommendation: Minimal set to start (updated)

To build a useful triage agent quickly without overloading the system:

### Core training / case-retrieval (pick one or both)
1) **`emergency_service_triage_application`** — best if you want KTAS-style prediction/explanations using real vitals + labels  
2) **`sample_hybrid_triage_dataset`** — best if you want “agent workflow” outputs (resources, optimizer_action, override)

### Core knowledge for RAG (start here)
3) **`cc_dx_knowledge`** — main retrieval table for “complaint → candidate dx → workup/tests/meds + threat flags”  
4) **`diagnosis_features`** — compact “what to do” summary per diagnosis

### Add only if needed for deeper explanations
5) **`medical_test_details`** (if you want to explain tests)  
6) **`medication_details`** (if you want to explain meds and safety)

> Practical default: **Hybrid dataset + `cc_dx_knowledge` + `diagnosis_features` + `medical_test_details`**.  
> Add `medication_details` only when you’re ready to generate medication-specific counseling.

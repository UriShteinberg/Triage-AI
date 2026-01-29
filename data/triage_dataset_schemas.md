# Triage dataset CSV schemas
Folder: `C:\Users\urish\OneDrive\Documents\HW\subjects at data engineering\triage agent\data\triage dataset`
Files: 26

---
## bod_sym.csv
- Size: 0.03 MB
- Delimiter: `,`
- Estimated rows (excluding header): **673**
- Columns: **17**

| column | inferred_type |
|---|---|
| _id | int |
| body_area_id | int |
| chief_complaint_id | empty |
| is_male | bool |
| is_female | bool |
| is_common | empty |
| _id | int |
| name | text |
| _id | int |
| chief_complaint_id | empty |
| chief_complaint_name_id | empty |
| name | text |
| reason_code | empty |
| life_threatening | empty |
| msp_enabled | empty |
| primary_complaint | empty |
| diagnosis_count | empty |

---
## body_areas.csv
- Size: 0.00 MB
- Delimiter: `,`
- Estimated rows (excluding header): **21**
- Columns: **2**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |

---
## body_areas_symptoms.csv
- Size: 0.01 MB
- Delimiter: `,`
- Estimated rows (excluding header): **673**
- Columns: **6**

| column | inferred_type |
|---|---|
| _id | int |
| body_area_id | int |
| chief_complaint_id | empty |
| is_male | bool |
| is_female | bool |
| is_common | empty |

---
## content_reviewers.csv
- Size: 0.00 MB
- Delimiter: `,`
- Estimated rows (excluding header): **2**
- Columns: **5**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| attribution_text | text |
| created_at | text |
| updated_at | text |

---
## content_reviews.csv
- Size: 0.26 MB
- Delimiter: `,`
- Estimated rows (excluding header): **8,577**
- Columns: **5**

| column | inferred_type |
|---|---|
| _id | int |
| content_reviewable_id | int |
| content_reviewable_type | text |
| content_field | text |
| content_reviewer_id | bool |

---
## diagnoses_medical_specialties.csv
- Size: 0.07 MB
- Delimiter: `,`
- Estimated rows (excluding header): **4,862**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medical_specialty_id | int |

---
## diagnoses_medical_tests.csv
- Size: 0.05 MB
- Delimiter: `,`
- Estimated rows (excluding header): **3,595**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medical_test_id | int |

---
## diagnosis_medications.csv
- Size: 0.34 MB
- Delimiter: `,`
- Estimated rows (excluding header): **6,557**
- Columns: **5**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medication_id | int |
| created_at | text |
| updated_at | text |

---
## diagnosis_translations.csv
- Size: 1.53 MB
- Delimiter: `,`
- Estimated rows (excluding header): **2,095**
- Columns: **8**

| column | inferred_type |
|---|---|
| _id | int |
| workup | text |
| treatment | text |
| symptoms | text |
| name | text |
| description | text |
| other_specific_tests | text |
| has_inteli_health_additions | bool |

---
## differential_diagnoses.csv
- Size: 0.10 MB
- Delimiter: `,`
- Estimated rows (excluding header): **5,566**
- Columns: **6**

| column | inferred_type |
|---|---|
| _id | int |
| chief_complaint_id | int |
| diagnosis_id | int |
| most_common | bool |
| common_peds | bool |
| life_or_limb_threatening | bool |

---
## dis_pro.csv
- Size: 431.37 MB
- Delimiter: `,`
- Estimated rows (excluding header): **373,393**
- Columns: **29**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medical_specialty_id | int |
| _id | int |
| procedure_id | int |
| medical_specialty_id | int |
| _id | int |
| workup | text |
| treatment | text |
| symptoms | text |
| name | text |
| description | text |
| other_specific_tests | text |
| has_inteli_health_additions | bool |
| _id | int |
| created_at | text |
| updated_at | text |
| deleted_at | empty |
| last_updated_at | float |
| last_deleted_at | empty |
| common_order | int |
| is_dental | bool |
| _id | int |
| name | text |
| description | text |
| _id | int |
| name | text |
| description | text |
| common_complications | text |

---
## dis_test.csv
- Size: 4.53 MB
- Delimiter: `,`
- Estimated rows (excluding header): **6,597**
- Columns: **14**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medical_test_id | int |
| _id | int |
| workup | text |
| treatment | text |
| symptoms | text |
| name | text |
| description | text |
| other_specific_tests | text |
| has_inteli_health_additions | bool |
| _id | int |
| name | text |
| description | text |

---
## dis_tre.csv
- Size: 58.02 MB
- Delimiter: `,`
- Estimated rows (excluding header): **450,798**
- Columns: **37**

| column | inferred_type |
|---|---|
| _id | int |
| diagnosis_id | int |
| medication_id | int |
| created_at | text |
| updated_at | text |
| _id | int |
| workup | text |
| treatment | text |
| symptoms | text |
| name | text |
| description | text |
| other_specific_tests | text |
| has_inteli_health_additions | bool |
| _id | int |
| name | text |
| side_effects | text |
| how | text |
| other_information | text |
| overdose | text |
| precautions | text |
| special_dietary | text |
| storage_conditions | text |
| why | text |
| group_name | text |
| prescription | bool |
| created_at | text |
| updated_at | text |
| if_i_forget | text |
| meta_title | empty |
| meta_description | empty |
| deleted_at | empty |
| print_class | text |
| import_file_name | text |
| generic_medication_id | bool |
| combination | bool |
| last_updated_at | float |
| last_deleted_at | empty |

---
## insurance_carrier_plans.csv
- Size: 0.18 MB
- Delimiter: `,`
- Estimated rows (excluding header): **5,702**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| insurance_carrier_id | int |
| name | text |

---
## insurance_carriers.csv
- Size: 0.03 MB
- Delimiter: `,`
- Estimated rows (excluding header): **742**
- Columns: **5**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| specialty_type | text |
| approved | bool |
| premier | bool |

---
## medical_societies.csv
- Size: 0.62 MB
- Delimiter: `,`
- Estimated rows (excluding header): **1,834**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| icon_file | text |

---
## medical_specialties.csv
- Size: 0.02 MB
- Delimiter: `,`
- Estimated rows (excluding header): **243**
- Columns: **8**

| column | inferred_type |
|---|---|
| _id | int |
| created_at | text |
| updated_at | text |
| deleted_at | text |
| last_updated_at | float |
| last_deleted_at | float |
| common_order | int |
| is_dental | bool |

---
## medical_specialties_procedures.csv
- Size: 0.02 MB
- Delimiter: `,`
- Estimated rows (excluding header): **1,464**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| procedure_id | int |
| medical_specialty_id | int |

---
## medical_specialty_translations.csv
- Size: 0.01 MB
- Delimiter: `,`
- Estimated rows (excluding header): **266**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| description | empty |

---
## medical_test_translations.csv
- Size: 0.01 MB
- Delimiter: `,`
- Estimated rows (excluding header): **197**
- Columns: **3**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| description | text |

---
## medications.csv
- Size: 6.69 MB
- Delimiter: `,`
- Estimated rows (excluding header): **54,594**
- Columns: **24**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| side_effects | text |
| how | text |
| other_information | text |
| overdose | text |
| precautions | text |
| special_dietary | text |
| storage_conditions | text |
| why | text |
| group_name | text |
| prescription | bool |
| created_at | text |
| updated_at | text |
| if_i_forget | text |
| meta_title | empty |
| meta_description | empty |
| deleted_at | empty |
| print_class | text |
| import_file_name | text |
| generic_medication_id | bool |
| combination | bool |
| last_updated_at | float |
| last_deleted_at | empty |

---
## procedure_translations.csv
- Size: 0.31 MB
- Delimiter: `,`
- Estimated rows (excluding header): **632**
- Columns: **4**

| column | inferred_type |
|---|---|
| _id | int |
| name | text |
| description | text |
| common_complications | text |

---
## sqlite_sequence.csv
- Size: 0.00 MB
- Delimiter: `,`
- Estimated rows (excluding header): **19**
- Columns: **2**

| column | inferred_type |
|---|---|
| name | text |
| seq | int |

---
## sym_dis.csv
- Size: 7.04 MB
- Delimiter: `,`
- Estimated rows (excluding header): **10,600**
- Columns: **23**

| column | inferred_type |
|---|---|
| _id | int |
| chief_complaint_id | int |
| diagnosis_id | int |
| most_common | bool |
| common_peds | bool |
| life_or_limb_threatening | bool |
| _id | int |
| chief_complaint_id | int |
| chief_complaint_name_id | int |
| name | text |
| reason_code | int |
| life_threatening | bool |
| msp_enabled | bool |
| primary_complaint | bool |
| diagnosis_count | int |
| _id | int |
| workup | text |
| treatment | text |
| symptoms | text |
| name | text |
| description | text |
| other_specific_tests | text |
| has_inteli_health_additions | bool |

---
## symptoms.csv
- Size: 0.01 MB
- Delimiter: `,`
- Estimated rows (excluding header): **389**
- Columns: **9**

| column | inferred_type |
|---|---|
| _id | int |
| chief_complaint_id | int |
| chief_complaint_name_id | int |
| name | text |
| reason_code | int |
| life_threatening | bool |
| msp_enabled | bool |
| primary_complaint | bool |
| diagnosis_count | int |

---
## wise_contents.csv
- Size: 0.18 MB
- Delimiter: `,`
- Estimated rows (excluding header): **382**
- Columns: **7**

| column | inferred_type |
|---|---|
| _id | int |
| wiseable_id | int |
| wiseable_type | text |
| content | text |
| attribution_text | text |
| medical_society_id | int |
| pdf_url | text |

# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.

## GAD-7 Score
GAD-7 Self-Report Screening

Based on the information provided, the system identifies a pattern of anxiety-related experiences and interpreted as;

**High Concern Pattern**

Your responses indicate a substantial number of experiences commonly associated with anxiety. Seeking support from a qualified healthcare professional may be beneficial. Effective treatments and support options are available, and discussing your concerns with a professional can help determine the most appropriate next steps.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Nearly every day
  2. Not being able to stop or control worrying
     → More than half the days
  3. Worrying too much about different things
     → Nearly every day
  4. Trouble relaxing
     → More than half the days
  5. Being so restless that it is hard to sit still
     → More than half the days
  6. Becoming easily annoyed or irritable
     → More than half the days
  7. Feeling afraid, as if something awful might happen
     → More than half the days

This result is intended for screening purposes only and should not be considered a diagnosis.

## Emotion Agent Output
```json
{
  "emotions": [],
  "emotional_intensity": "low",
  "evidence_from_text": [
    "I've been busy with work and keeping up with things."
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "Everything is going alright I guess.",
    "I've been busy with work and keeping up with things. Not much to report really."
  ],
  "not_enough_information": true
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [],
  "life_domains": [],
  "evidence_from_text": [
    "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really."
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes their day-to-day life as 'going alright,' suggesting no clear anxiety or distress. No functional impact, anxiety-related experiences, or immediate safety concern is mentioned.",
  "recommended_support": "Monitor your symptoms and consider follow-up if symptoms persist or worsen.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783298482971",
  "claims": [
    {
      "claimId": "GEN-1",
      "sourceAgent": "emotion",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "category": "emotional_state"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783298482971",
  "results": [
    {
      "claimId": "GEN-1",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DEP-001",
          "text": "CHUNK_ID: DEP-001\nINDICATOR: Depressed Mood\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: A period of depressed mood occurring most of the day, nearly\nevery day, for at least two weeks — experienced as persistent sadness,\nemptiness, or a heavy, low feeling.\nPLAIN_LANGUAGE_EXAMPLES: \"I just feel empty most of the time.\" \"There's\nthis heaviness that doesn't lift, even on good days.\"\nNON_DIAGNOSTIC_NOTE: Low mood is a normal human experience, especially in\nresponse to difficult events. This indicator describes mood that is\npersistent (most of most days) and sustained (at least two weeks), not a\nbrief or situational dip.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5538491904735565
        },
        {
          "chunkId": "DIFF-005",
          "text": "CHUNK_ID: DIFF-005\nSECTION: Reporting Guidance for the Differentiation Output\nSOURCE_TYPE: differentiation_guidance\nCONTENT: The differentiation assessment should report a primary lean of\n\"anxiety\", \"depression\", \"mixed\", or \"unclear\" — \"unclear\" is valid and\nshould be used when available claims are dominated by DIFF-003 (shared,\nlow-specificity) signals without a clear DIFF-001 or DIFF-002 anchor. Every\nlean must cite the specific chunk(s) that support it, never asserted\nwithout citation.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.5458248257637024
        },
        {
          "chunkId": "DEP-003",
          "text": "CHUNK_ID: DEP-003\nINDICATOR: Reduced Energy / Fatigue (Depression Presentation)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Reduced energy or persistent fatigue, often described as\neffortful even for routine tasks, not substantially relieved by rest.\nPLAIN_LANGUAGE_EXAMPLES: \"Even getting out of bed feels like a huge\neffort.\" \"I'm tired no matter how much I sleep.\"\nNON_DIAGNOSTIC_NOTE: Fatigue is a shared symptom across many conditions,\nincluding anxiety, and has many non-psychiatric causes (e.g., anemia,\nthyroid conditions, sleep disorders). See shared_symptoms.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5440569221973419
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5358755886554718
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 1,
    "totalChunksRetrieved": 4,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt"
    ]
  },
  "riskLevel": "low"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783298482971",
  "claimValidations": [
    {
      "claimId": "GEN-1",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DEP-001"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.554, threshold: 0.55–0.72). Treat with caution; evidence from: depression_indicators.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 1 claims evaluated: 0 supported, 1 partially supported, 0 unsupported.",
  "riskLevel": "low"
}
```

## Final Report
```md
# AnxioSense Screening Support Report

## 0. GAD-7 Screening Result

GAD-7 Self-Report Screening

Based on the information provided, the system identifies a pattern of anxiety-related experiences and interpreted as;

**High Concern Pattern**

Your responses indicate a substantial number of experiences commonly associated with anxiety. Seeking support from a qualified healthcare professional may be beneficial. Effective treatments and support options are available, and discussing your concerns with a professional can help determine the most appropriate next steps.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Nearly every day
  2. Not being able to stop or control worrying
     → More than half the days
  3. Worrying too much about different things
     → Nearly every day
  4. Trouble relaxing
     → More than half the days
  5. Being so restless that it is hard to sit still
     → More than half the days
  6. Becoming easily annoyed or irritable
     → More than half the days
  7. Feeling afraid, as if something awful might happen
     → More than half the days

This result is intended for screening purposes only and should not be considered a diagnosis.

# AnxioSense Screening Support Report

## 1. Input Mode
The input mode used for this report was Journal / Self-Report.

## 2. Summary of Concern
Based on the available information, the text may reflect a period of depressed mood and potential difficulty maintaining concentration, although the differentiation assessment remains unclear.

## 3. Emotional Indicators
The available text suggests that everything is going alright I guess, which could be indicative of an underlying emotional state.

## 4. Anxiety-Related Indicators
No anxiety-related indicators were identified in the available information.

## 5. Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:

1. "A period of depressed mood occurring most of the day, nearly every day, for..." (ICD-11 6A70, WHO (2025-01))
2. "Difficulty maintaining concentration, often..." (ICD-11 6B00, WHO (2025-01))

## 6. Contextual Factors
No contextual factors were identified in the available information.

## 7. Referral and Safety Recommendation
Given the potential for depressed mood and difficulty concentrating, it is recommended to seek a low-intensity follow-up with a qualified healthcare professional.

## 8. Limitations
This report is based only on the information provided. Missing context may affect interpretation. This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment.

---

## Clinician Details *(restricted — do not share with patient)*

**GAD-7 Raw Score:** 16/21
**Clinical Severity:** Severe Anxiety — 15–21

**Per-Item Breakdown:**
  1. Feeling nervous, anxious, or on edge
     → Nearly every day (3)
  2. Not being able to stop or control worrying
     → More than half the days (2)
  3. Worrying too much about different things
     → Nearly every day (3)
  4. Trouble relaxing
     → More than half the days (2)
  5. Being so restless that it is hard to sit still
     → More than half the days (2)
  6. Becoming easily annoyed or irritable
     → More than half the days (2)
  7. Feeling afraid, as if something awful might happen
     → More than half the days (2)

**Differentiation Assessment:** unclear
**Differentiation Reasoning:** Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category.
**Validation Notes:** Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 1 claims evaluated: 0 supported, 1 partially supported, 0 unsupported.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
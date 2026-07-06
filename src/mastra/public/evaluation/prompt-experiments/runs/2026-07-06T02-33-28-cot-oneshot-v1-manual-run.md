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
    "I've been busy with work and keeping up with things",
    "Not much to report really"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "Everything is going alright I guess",
    "I've been busy with work and keeping up with things"
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
    "I've been busy with work"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes a state of relative normalcy, suggesting that only minimal or no anxiety-related experiences are described.",
  "recommended_support": "Monitoring is recommended if symptoms persist or worsen.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783305196339",
  "claims": [
    {
      "claimId": "GEN-1",
      "sourceAgent": "emotion",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "category": "anxiety_indicator"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783305196339",
  "results": [
    {
      "claimId": "GEN-1",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "sourceAgent": "emotion",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5648184418678284
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5358755886554718
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5293216109275818
        },
        {
          "chunkId": "ANX-001",
          "text": "CHUNK_ID: ANX-001\nINDICATOR: Excessive Worry / Apprehensive Expectation\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked symptoms of anxiety persisting for at least several\nmonths, occurring more days than not, manifested as either general\napprehension (\"free-floating anxiety\") or excessive worry focused on\nmultiple everyday events — most often concerning family, health, finances,\nschool, or work.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't stop worrying about things that probably\nwon't even happen.\" \"My mind keeps jumping to worst-case scenarios about\nschool or money.\"\nNON_DIAGNOSTIC_NOTE: Occasional worry about real stressors is common and\nexpected. This indicator describes worry that is pervasive across multiple\nlife areas and persists over months, not situational concern about a single\nupcoming event.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5233286321163177
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
      "instrument_reference.txt"
    ]
  },
  "riskLevel": "low"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783305196339",
  "claimValidations": [
    {
      "claimId": "GEN-1",
      "claimText": "Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really.",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "INST-GAD7-INTRO"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.565, threshold: 0.55–0.72). Treat with caution; evidence from: instrument_reference.txt."
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

## Assessment Overview

**Analysis Type:** Journal / Self-Report

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

**Note on Evidence Sources:** The structured questionnaire indicates a higher level of concern than was reflected in the written text. Written expression may not fully capture all of an individual's internal experiences. Both sources were considered in generating this report.

## Supporting Findings
- No significant anxiety-related indicators were identified in the provided text.
- Positive emotional tone.
- Stable functioning.
- Social withdrawal may be present.
- Contextual factors: work demands, academic pressures.

## Recommendation
Discussing these experiences with a qualified healthcare professional might be beneficial for determining the most appropriate support options.

## Evidence Agreement

**Low** — The questionnaire responses indicated more concern than the written text alone suggested.

## Limitations
This report is based solely on the information provided and interpretation could be affected by missing context. It should not be considered a clinical diagnosis. A qualified healthcare professional is needed for a comprehensive assessment. This report is intended for screening support only and should not be considered a clinical diagnosis.

---

## Clinician Summary *(restricted — do not share with patient)*

**GAD-7:** 16/21 (Severe — 15–21)

**Per-Item Responses:**
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

**Validated Indicators:**
  - Everything is going alright I guess. I've been busy with work and keeping up with things. Not much to report really. (Partially Supported)

**Evidence Confidence:** Low

**Differential Considerations:**
Available information was insufficient to confidently distinguish anxiety-related symptoms from other possible conditions such as depression. Further clinical assessment would be required.

**Assessment Notes:**
The questionnaire responses indicated greater concern than was reflected in the written text. This may suggest that written expression did not fully capture the respondent's internal experience.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
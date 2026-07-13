# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.

## GAD-7 Score
GAD-7 Self-Report Screening

Based on the information provided, the system identifies a pattern of anxiety-related experiences and interpreted as;

**Minimal Concern Pattern**

Your responses suggest that experiences commonly associated with anxiety are currently limited. Occasional stress or worry is a normal part of life. If these feelings become more frequent or begin affecting your daily activities, you may wish to check in with a healthcare professional.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Not at all
  2. Not being able to stop or control worrying
     → Not at all
  3. Worrying too much about different things
     → Not at all
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → Not at all
  6. Becoming easily annoyed or irritable
     → Not at all
  7. Feeling afraid, as if something awful might happen
     → Several days

This result is intended for screening purposes only and should not be considered a diagnosis.

## Emotion Agent Output
```json
{
  "emotions": [],
  "emotional_intensity": "low",
  "evidence_from_text": [
    "I've been feeling pretty good this week.",
    "Work has been steady",
    "I got enough sleep",
    "I had a nice dinner with friends on Friday",
    "I noticed I was a bit worried before a presentation but it passed quickly once I started",
    "Overall things feel manageable"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "I've been feeling pretty good this week",
    "Work has been steady",
    "I got enough sleep",
    "I had a nice dinner with friends on Friday",
    "I was a bit worried before a presentation but it passed quickly once I started",
    "Overall things feel manageable"
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [],
  "life_domains": [],
  "evidence_from_text": [
    "Work has been steady",
    "I had a nice dinner with friends on Friday"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes feeling good overall, having a steady work schedule, getting enough sleep, and enjoying social activities. The mentioned worry before a presentation suggests a mild anxiety-related experience that passed quickly, indicating minimal distress.",
  "recommended_support": "Monitor symptoms and consider follow-up if they persist or worsen.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783304809981",
  "claims": [
    {
      "claimId": "GEN-1",
      "sourceAgent": "emotion",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "category": "anxiety_indicator"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783304809981",
  "results": [
    {
      "claimId": "GEN-1",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "sourceAgent": "emotion",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.6116129159927368
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5957484543323517
        },
        {
          "chunkId": "ANX-006",
          "text": "CHUNK_ID: ANX-006\nINDICATOR: Sleep Disturbance (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty falling asleep due to racing thoughts or worry at\nbedtime (initial insomnia), distinct in pattern from the early-morning\nwaking more often associated with depressive presentations.\nPLAIN_LANGUAGE_EXAMPLES: \"I lie awake for hours because my brain won't\nstop.\" \"I can't fall asleep because I keep thinking about tomorrow.\"\nNON_DIAGNOSTIC_NOTE: See anxiety_vs_depression.txt for the full\ndifferentiation between anxiety-type and depression-type sleep disturbance.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5921503007411957
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.582950234413147
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
  "sessionId": "session-1783304809981",
  "claimValidations": [
    {
      "claimId": "GEN-1",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "INST-GAD7-INTRO",
        "INST-GAD7-01"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.612, threshold: 0.55–0.72). Treat with caution; evidence from: instrument_reference.txt, instrument_reference.txt."
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

**Minimal Concern Pattern**

Your responses suggest that experiences commonly associated with anxiety are currently limited. Occasional stress or worry is a normal part of life. If these feelings become more frequent or begin affecting your daily activities, you may wish to check in with a healthcare professional.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Not at all
  2. Not being able to stop or control worrying
     → Not at all
  3. Worrying too much about different things
     → Not at all
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → Not at all
  6. Becoming easily annoyed or irritable
     → Not at all
  7. Feeling afraid, as if something awful might happen
     → Several days

This result is intended for screening purposes only and should not be considered a diagnosis.

## Supporting Findings
- No significant anxiety-related indicators were identified in the provided text.
- Positive emotional tone present in self-report.
- Stable functioning reported through work, social interactions, and sleep patterns.

## Recommendation
The current report suggests that occasional mild experiences are a normal part of life for the individual. It is recommended to monitor changes in these experiences over time. Consider speaking with a healthcare professional if they become more frequent, worsen, or begin significantly affecting daily functioning.

## Evidence Agreement

**High** — The questionnaire responses and written text were generally consistent.

## Limitations
This report is based solely on the information provided and may be influenced by missing context. It should not be considered a clinical diagnosis but rather intended for screening support only. A qualified healthcare professional is needed for a comprehensive clinical assessment. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a thorough evaluation.

---

## Clinician Summary *(restricted — do not share with patient)*

**GAD-7:** 2/21 (Minimal — 0–4)

**Per-Item Responses:**
  1. Feeling nervous, anxious, or on edge
     → Not at all
  2. Not being able to stop or control worrying
     → Not at all
  3. Worrying too much about different things
     → Not at all
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → Not at all
  6. Becoming easily annoyed or irritable
     → Not at all
  7. Feeling afraid, as if something awful might happen
     → Several days

**Validated Indicators:**
  - I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable. (Partially Supported)

**Evidence Confidence:** High

**Differential Considerations:**
Available information was insufficient to confidently distinguish anxiety-related symptoms from other possible conditions such as depression. Further clinical assessment would be required.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
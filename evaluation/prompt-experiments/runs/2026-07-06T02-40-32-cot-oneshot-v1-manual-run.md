# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
I don't see the point anymore. I've been thinking that everyone would be better off without me. I haven't slept in days and I just feel completely empty. I don't know what to do.

## GAD-7 Score
GAD-7 Self-Report Screening

Based on the information provided, the system identifies a pattern of anxiety-related experiences and interpreted as;

**Elevated Concern Pattern**

Your responses suggest several experiences that are commonly associated with anxiety and may be affecting your well-being. It may be beneficial to discuss these concerns with a healthcare professional who can provide a more comprehensive assessment and appropriate guidance.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → More than half the days
  2. Not being able to stop or control worrying
     → More than half the days
  3. Worrying too much about different things
     → More than half the days
  4. Trouble relaxing
     → More than half the days
  5. Being so restless that it is hard to sit still
     → Several days
  6. Becoming easily annoyed or irritable
     → Several days
  7. Feeling afraid, as if something awful might happen
     → Nearly every day

This result is intended for screening purposes only and should not be considered a diagnosis.

## Emotion Agent Output
```json
{
  "emotions": [
    "sadness",
    "hopelessness"
  ],
  "emotional_intensity": "high",
  "evidence_from_text": [
    "I don't see the point anymore.",
    "I've been thinking that everyone would be better off without me.",
    "I haven't slept in days",
    "I just feel completely empty",
    "I don't know what to do"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "I don't see the point anymore.",
    "I've been thinking that everyone would be better off without me",
    "I haven't slept in days"
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
    "I don't see the point anymore",
    "I've been thinking that everyone would be better off without me",
    "I haven't slept in days and I just feel completely empty"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "urgent",
  "reasoning": "The user describes feeling suicidal ('I don't see the point anymore'), experiencing insomnia ('haven't slept in days'), and expressing a desire for others to be better off without them, suggesting an immediate safety concern. This text indicates a need for emergency/crisis support.",
  "recommended_support": "Immediate emergency/crisis support or contacting a trusted person for immediate help.",
  "safety_note": "If you or someone else is in immediate danger, please seek help from emergency services or reach out to a crisis hotline."
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783305632666",
  "claims": [
    {
      "claimId": "EMO-1",
      "sourceAgent": "emotion",
      "claimText": "sadness",
      "category": "emotional_state"
    },
    {
      "claimId": "EMO-2",
      "sourceAgent": "emotion",
      "claimText": "hopelessness",
      "category": "emotional_state"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783305632666",
  "results": [
    {
      "claimId": "EMO-1",
      "claimText": "sadness",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DEP-001",
          "text": "CHUNK_ID: DEP-001\nINDICATOR: Depressed Mood\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: A period of depressed mood occurring most of the day, nearly\nevery day, for at least two weeks — experienced as persistent sadness,\nemptiness, or a heavy, low feeling.\nPLAIN_LANGUAGE_EXAMPLES: \"I just feel empty most of the time.\" \"There's\nthis heaviness that doesn't lift, even on good days.\"\nNON_DIAGNOSTIC_NOTE: Low mood is a normal human experience, especially in\nresponse to difficult events. This indicator describes mood that is\npersistent (most of most days) and sustained (at least two weeks), not a\nbrief or situational dip.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6673582792282104
        },
        {
          "chunkId": "DEP-002",
          "text": "CHUNK_ID: DEP-002\nINDICATOR: Anhedonia (Diminished Interest or Pleasure)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Markedly diminished interest or pleasure in activities that\nwere previously enjoyable, occurring most of the day, nearly every day,\nfor at least two weeks.\nPLAIN_LANGUAGE_EXAMPLES: \"Nothing really feels enjoyable anymore, not even\nthings I used to look forward to.\" \"I don't care about hanging out with\nfriends the way I used to.\"\nNON_DIAGNOSTIC_NOTE: This is one of the two core gateway features of a\ndepressive episode under ICD-11 (alongside depressed mood) and is\nconsidered relatively specific to depressive presentations rather than\nanxiety — see anxiety_vs_depression.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6128382086753845
        },
        {
          "chunkId": "DIFF-002",
          "text": "CHUNK_ID: DIFF-002\nSECTION: Features More Strongly Associated With Depression\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Anhedonia: a pervasive, marked loss of interest or pleasure across most\n  activities — considered one of the most specific discriminators.\n- Past/present-oriented cognitive content: hopelessness, worthlessness,\n  guilt, themes of loss or failure rather than anticipated threat.\n- Psychomotor slowing (retardation): slowed speech, movement, or thinking.\n- Early-morning waking or hypersomnia.\n- Pervasive low mood rather than situational worry.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6039242744445801
        },
        {
          "chunkId": "DIFF-005",
          "text": "CHUNK_ID: DIFF-005\nSECTION: Reporting Guidance for the Differentiation Output\nSOURCE_TYPE: differentiation_guidance\nCONTENT: The differentiation assessment should report a primary lean of\n\"anxiety\", \"depression\", \"mixed\", or \"unclear\" — \"unclear\" is valid and\nshould be used when available claims are dominated by DIFF-003 (shared,\nlow-specificity) signals without a clear DIFF-001 or DIFF-002 anchor. Every\nlean must cite the specific chunk(s) that support it, never asserted\nwithout citation.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.5564161241054535
        }
      ]
    },
    {
      "claimId": "EMO-2",
      "claimText": "hopelessness",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DEP-004",
          "text": "CHUNK_ID: DEP-004\nINDICATOR: Feelings of Worthlessness or Excessive Guilt\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Persistent feelings of worthlessness, or excessive or\ninappropriate guilt, extending beyond reasonable self-criticism about a\nspecific event.\nPLAIN_LANGUAGE_EXAMPLES: \"I feel like a burden to everyone around me.\"\n\"Everything that goes wrong feels like it's my fault, even when it\nisn't.\"\nNON_DIAGNOSTIC_NOTE: Relevant to referral_guidelines.txt severity tiering.\nProfound hopelessness combined with this indicator should be cross-checked\nagainst safety_boundary.txt escalation criteria.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6228373050689697
        },
        {
          "chunkId": "DEP-005",
          "text": "CHUNK_ID: DEP-005\nINDICATOR: Difficulty Concentrating (Depression Presentation)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty concentrating or making decisions, often described\nalongside mental slowing or low motivation rather than active worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't make even small decisions anymore.\" \"My\nthinking feels slow and foggy.\"\nNON_DIAGNOSTIC_NOTE: Compare to ANX-004 in anxiety_indicators.txt — the\nunderlying mechanism (worry-driven vs. energy/motivation-driven) differs\neven though the surface symptom looks similar. See shared_symptoms.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6044511497020721
        },
        {
          "chunkId": "DIFF-002",
          "text": "CHUNK_ID: DIFF-002\nSECTION: Features More Strongly Associated With Depression\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Anhedonia: a pervasive, marked loss of interest or pleasure across most\n  activities — considered one of the most specific discriminators.\n- Past/present-oriented cognitive content: hopelessness, worthlessness,\n  guilt, themes of loss or failure rather than anticipated threat.\n- Psychomotor slowing (retardation): slowed speech, movement, or thinking.\n- Early-morning waking or hypersomnia.\n- Pervasive low mood rather than situational worry.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6027712523937225
        },
        {
          "chunkId": "ANX-005",
          "text": "CHUNK_ID: ANX-005\nINDICATOR: Irritability (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Low frustration tolerance or a persistent edgy, on-edge mood,\ncommonly arising from chronic nervous system activation and the strain of\nongoing worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I snap at people more than I used to.\" \"Small\nthings set me off lately.\"\nNON_DIAGNOSTIC_NOTE: Irritability is a non-specific symptom shared with\ndepression (see shared_symptoms.txt) and many other states, including\nordinary stress and sleep deprivation.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.59062460064888
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 2,
    "totalChunksRetrieved": 8,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt"
    ]
  },
  "riskLevel": "urgent"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783305632666",
  "claimValidations": [
    {
      "claimId": "EMO-1",
      "claimText": "sadness",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DEP-001",
        "DEP-002"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.667, threshold: 0.55–0.72). Treat with caution; evidence from: depression_indicators.txt, depression_indicators.txt."
    },
    {
      "claimId": "EMO-2",
      "claimText": "hopelessness",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DEP-004",
        "DEP-005"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.623, threshold: 0.55–0.72). Treat with caution; evidence from: depression_indicators.txt, depression_indicators.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 2 claims evaluated: 0 supported, 2 partially supported, 0 unsupported.",
  "riskLevel": "urgent"
}
```

## Final Report
```md
# AnxioSense Screening Support Report

## Important — Urgent Safety Notice

Based on what you shared, there may be an immediate safety concern that requires urgent attention.

**This screening tool is not able to provide crisis support.** Please reach out for help right now:

- Contact a crisis line in your country or region
- Go to your nearest emergency department, or call emergency services (911 / 999 / 112)
- Reach out immediately to a trusted person who can be with you

---

*This report has not been generated. When an immediate safety concern is present, your wellbeing takes priority over a screening summary. Please seek support now.*

*This tool is intended for screening support only and is not a clinical service.*
```
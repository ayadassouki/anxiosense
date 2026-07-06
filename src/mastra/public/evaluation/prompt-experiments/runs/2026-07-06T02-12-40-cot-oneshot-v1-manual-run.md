# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
Just got back from a week-long hiking trip. Completely off-grid, no phone signal, just mountains and fresh air. Feeling refreshed and glad I did it. Ready to get back to work next week.

## GAD-7 Score
_Not provided for this run._

## Emotion Agent Output
```json
{
  "emotions": [
    "happiness"
  ],
  "emotional_intensity": "high",
  "evidence_from_text": [
    "feeling refreshed",
    "glad I did it"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "Feeling refreshed and glad I did it"
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
    "Just got back from a week-long hiking trip",
    "Completely off-grid, no phone signal",
    "Ready to get back to work next week"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes a week-long hiking trip during which they were disconnected from technology and surrounded by nature. They express feeling refreshed upon returning, indicating a temporary break from potential stressors. No explicit symptoms or functional impairment are mentioned.",
  "recommended_support": "Monitor your feelings and wellbeing in the coming weeks. If symptoms persist or worsen, consider discussing with a trusted person or a qualified healthcare professional.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783303948287",
  "claims": [
    {
      "claimId": "EMO-1",
      "sourceAgent": "emotion",
      "claimText": "happiness",
      "category": "emotional_state"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783303948287",
  "results": [
    {
      "claimId": "EMO-1",
      "claimText": "happiness",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DEP-002",
          "text": "CHUNK_ID: DEP-002\nINDICATOR: Anhedonia (Diminished Interest or Pleasure)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Markedly diminished interest or pleasure in activities that\nwere previously enjoyable, occurring most of the day, nearly every day,\nfor at least two weeks.\nPLAIN_LANGUAGE_EXAMPLES: \"Nothing really feels enjoyable anymore, not even\nthings I used to look forward to.\" \"I don't care about hanging out with\nfriends the way I used to.\"\nNON_DIAGNOSTIC_NOTE: This is one of the two core gateway features of a\ndepressive episode under ICD-11 (alongside depressed mood) and is\nconsidered relatively specific to depressive presentations rather than\nanxiety — see anxiety_vs_depression.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5881808400154114
        },
        {
          "chunkId": "DIFF-002",
          "text": "CHUNK_ID: DIFF-002\nSECTION: Features More Strongly Associated With Depression\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Anhedonia: a pervasive, marked loss of interest or pleasure across most\n  activities — considered one of the most specific discriminators.\n- Past/present-oriented cognitive content: hopelessness, worthlessness,\n  guilt, themes of loss or failure rather than anticipated threat.\n- Psychomotor slowing (retardation): slowed speech, movement, or thinking.\n- Early-morning waking or hypersomnia.\n- Pervasive low mood rather than situational worry.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.5479871332645416
        },
        {
          "chunkId": "ANX-005",
          "text": "CHUNK_ID: ANX-005\nINDICATOR: Irritability (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Low frustration tolerance or a persistent edgy, on-edge mood,\ncommonly arising from chronic nervous system activation and the strain of\nongoing worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I snap at people more than I used to.\" \"Small\nthings set me off lately.\"\nNON_DIAGNOSTIC_NOTE: Irritability is a non-specific symptom shared with\ndepression (see shared_symptoms.txt) and many other states, including\nordinary stress and sleep deprivation.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5321837067604065
        },
        {
          "chunkId": "DIFF-001",
          "text": "CHUNK_ID: DIFF-001\nSECTION: Features More Strongly Associated With Anxiety\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Autonomic/physical arousal: racing heart, sweating, trembling,\n  gastrointestinal discomfort.\n- Future-oriented cognitive content: worry, apprehension, catastrophic\n  anticipation of events that have not happened yet.\n- Specific behavioural avoidance tied to identifiable triggers or\n  situations.\n- Initial insomnia (difficulty falling asleep due to racing thoughts).\n- Muscle tension and motor restlessness rather than slowing.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.5296339988708496
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
  "sessionId": "session-1783303948287",
  "claimValidations": [
    {
      "claimId": "EMO-1",
      "claimText": "happiness",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DEP-002"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.588, threshold: 0.55–0.72). Treat with caution; evidence from: depression_indicators.txt."
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

**Analysis Type:** Social Media Analysis

No structured questionnaire was available because this analysis was performed using secondary social media text. Results therefore rely only on linguistic, emotional, symptomatic, and contextual indicators identified in the written text.

## Supporting Findings

The report identified the following experiences in the provided text:

- happiness

These findings were checked against the clinical guidance and screening knowledge base used by AnxioSense.

## Recommendation
Given the occasional mild experiences that have been detected, no immediate follow-up is indicated at this time. However, it may be beneficial to monitor how these experiences change over time. If they become more frequent, worsen, or begin significantly impacting daily functioning, consider speaking with a qualified healthcare professional for further assessment and guidance.

## Evidence Agreement

**Moderate** — Some indicators were present, but the available text provided limited detail.

## Limitations
This report is based solely on the information provided within the social media analysis. Missing context may affect interpretation, and it is essential to note that this is not a clinical diagnosis. A comprehensive clinical assessment by a qualified healthcare professional is necessary for an accurate evaluation. Due to the nature of social media text, this analysis carries additional uncertainty compared to other modes of communication.

This report is intended for screening support only and should not be considered a clinical diagnosis.

---

## Clinician Details *(restricted — do not share with patient)*

**Claims evaluated (1):**
  1. "happiness" (emotion) — partially_supported

**Retrieved chunk IDs:** DEP-002, DIFF-002, ANX-005, DIFF-001

**Differentiation:** Differential considerations were not conclusive from the available text.
**Validation Notes:** Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 1 claims evaluated: 0 supported, 1 partially supported, 0 unsupported.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
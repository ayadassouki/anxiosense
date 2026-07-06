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
    "Feeling refreshed",
    "Glad I did it",
    "Ready to get back to work"
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
    "Feeling refreshed and glad I did it. Ready to get back to work next week"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes a week-long hiking trip that was completed successfully without explicit mention of anxiety or distress. The user expresses feeling refreshed and ready for work, suggesting no immediate functional impairment.",
  "recommended_support": "Monitor symptoms and consider follow-up if needed.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783298958572",
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
  "sessionId": "session-1783298958572",
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
  "sessionId": "session-1783298958572",
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

## 1. Input Mode
This analysis is based on social media text written by an unknown author, not a structured clinical self-report. Results carry additional uncertainty due to the indirect nature of the text.

## 2. Summary of Concern
The available text may reflect diminished interest or pleasure, as well as potential irritability which could be consistent with anxiety-related presentations. However, these findings are based on linguistic indicators only and carry additional uncertainty due to the indirect nature of the social media text.

## 3. Emotional Indicators
The available text suggests a possible diminished interest or pleasure in certain activities.

## 4. Anxiety-Related Indicators
No anxiety-related indicators were identified in the available information.

## 5. Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:
1. "Anhedonia (Diminished Interest or Pleasure): Markedly diminished interest or pleasure in a..." (ICD-11 6A70, WHO (2025-01))
2. "Irritability (Anxiety Presentation): Low frustration tolerance or a persistent edgy, on-edge feeling..." (ICD-11 6B00, WHO (2025-01))

## 6. Contextual Factors
No contextual factors were identified in the available information.

## 7. Referral and Safety Recommendation
Based on the validated findings, a low referral level is suggested. However, given the additional uncertainty introduced by social media text, it is advisable to re-evaluate these findings with further direct input from the user if possible.

## 8. Limitations
This report is based only on the information provided in the social media text. Missing context may affect interpretation, and this analysis should not be considered a clinical diagnosis. A qualified healthcare professional is needed for a comprehensive assessment. Additionally, due to the indirect nature of the social media text, results carry additional uncertainty that would not be present with direct input from the user.

This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment.
```
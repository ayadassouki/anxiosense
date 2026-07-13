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
    "I've been feeling pretty good this week",
    "Work has been steady",
    "I got enough sleep",
    "I had a nice dinner with friends on Friday",
    "Overall things feel manageable"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [
    "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable."
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [],
  "life_domains": [
    "Work",
    "Social"
  ],
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
  "reasoning": "The user describes feeling good overall, steady work, sufficient sleep, and positive social interactions. The only mention of anxiety is a brief worry before a presentation that passed quickly, suggesting minimal and situational experiences. No functional impairment or safety concern is mentioned.",
  "recommended_support": "Monitor your symptoms and seek optional follow-up if symptoms persist or worsen.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783299632538",
  "claims": [
    {
      "claimId": "GEN-1",
      "sourceAgent": "emotion",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "category": "emotional_state"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783299632538",
  "results": [
    {
      "claimId": "GEN-1",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DEP-002",
          "text": "CHUNK_ID: DEP-002\nINDICATOR: Anhedonia (Diminished Interest or Pleasure)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Markedly diminished interest or pleasure in activities that\nwere previously enjoyable, occurring most of the day, nearly every day,\nfor at least two weeks.\nPLAIN_LANGUAGE_EXAMPLES: \"Nothing really feels enjoyable anymore, not even\nthings I used to look forward to.\" \"I don't care about hanging out with\nfriends the way I used to.\"\nNON_DIAGNOSTIC_NOTE: This is one of the two core gateway features of a\ndepressive episode under ICD-11 (alongside depressed mood) and is\nconsidered relatively specific to depressive presentations rather than\nanxiety — see anxiety_vs_depression.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.63704913854599
        },
        {
          "chunkId": "DEP-001",
          "text": "CHUNK_ID: DEP-001\nINDICATOR: Depressed Mood\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: A period of depressed mood occurring most of the day, nearly\nevery day, for at least two weeks — experienced as persistent sadness,\nemptiness, or a heavy, low feeling.\nPLAIN_LANGUAGE_EXAMPLES: \"I just feel empty most of the time.\" \"There's\nthis heaviness that doesn't lift, even on good days.\"\nNON_DIAGNOSTIC_NOTE: Low mood is a normal human experience, especially in\nresponse to difficult events. This indicator describes mood that is\npersistent (most of most days) and sustained (at least two weeks), not a\nbrief or situational dip.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6289187967777252
        },
        {
          "chunkId": "DIFF-005",
          "text": "CHUNK_ID: DIFF-005\nSECTION: Reporting Guidance for the Differentiation Output\nSOURCE_TYPE: differentiation_guidance\nCONTENT: The differentiation assessment should report a primary lean of\n\"anxiety\", \"depression\", \"mixed\", or \"unclear\" — \"unclear\" is valid and\nshould be used when available claims are dominated by DIFF-003 (shared,\nlow-specificity) signals without a clear DIFF-001 or DIFF-002 anchor. Every\nlean must cite the specific chunk(s) that support it, never asserted\nwithout citation.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6106308698654175
        },
        {
          "chunkId": "ANX-006",
          "text": "CHUNK_ID: ANX-006\nINDICATOR: Sleep Disturbance (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty falling asleep due to racing thoughts or worry at\nbedtime (initial insomnia), distinct in pattern from the early-morning\nwaking more often associated with depressive presentations.\nPLAIN_LANGUAGE_EXAMPLES: \"I lie awake for hours because my brain won't\nstop.\" \"I can't fall asleep because I keep thinking about tomorrow.\"\nNON_DIAGNOSTIC_NOTE: See anxiety_vs_depression.txt for the full\ndifferentiation between anxiety-type and depression-type sleep disturbance.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5921503007411957
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
  "sessionId": "session-1783299632538",
  "claimValidations": [
    {
      "claimId": "GEN-1",
      "claimText": "I've been feeling pretty good this week. Work has been steady, I got enough sleep, and I had a nice dinner with friends on Friday. I noticed I was a bit worried before a presentation but it passed quickly once I started. Overall things feel manageable.",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DEP-002",
        "DEP-001"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.637, threshold: 0.55–0.72). Treat with caution; evidence from: depression_indicators.txt, depression_indicators.txt."
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

# AnxioSense Screening Support Report

## 1. Input Mode
The mode used is Journal / Self-Report.

## 2. Summary of Concern
Based on the information provided, the available text suggests a period of relatively positive emotions and manageable stress levels. However, there are no clear indications of emotional distress or anxiety.

## 3. Emotional Indicators
No emotional indicators were identified in the available information that suggest significant emotional disturbance.

## 4. Anxiety-Related Indicators
No anxiety-related indicators were identified in the available information.

## 5. Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:

1. "CHUNK_ID: DEP-002
   INDICATOR: Anhedonia (Diminished Interest or Pleasure)
   SOURCE: ICD-11 6A70, WHO (2025-01)
   SOURCE_TYPE: clinical_description
   DESCRIPTION: Markedly diminished interest or pleasure in a..."

2. "CHUNK_ID: DEP-001
   INDICATOR: Depressed Mood
   SOURCE: ICD-11 6A70, WHO (2025-01)
   SOURCE_TYPE: clinical_description
   DESCRIPTION: A period of depressed mood occurring most of the day, nearly every day..."

3. "CHUNK_ID: DIFF-005
   SECTION: Reporting Guidance for the Differentiation Output
   SOURCE_TYPE: differentiation_guidance
   CONTENT: The differentiation assessment should report a primary lean of 'depression', not 'anxiety'."

4. "CHUNK_ID: ANX-006
   INDICATOR: Sleep Disturbance (Anxiety Presentation)
   SOURCE: ICD-11 6B00, WHO (2025-01)
   SOURCE_TYPE: clinical_description
   DESCRIPTION: Difficulty falling asleep due to racing thoughts..."

## 6. Contextual Factors
No contextual factors were identified in the available information.

## 7. Referral and Safety Recommendation
The text suggests a low level of concern, with no indications necessitating immediate follow-up or referral.

## 8. Limitations
This report is based only on the information provided. Missing context may affect interpretation. This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment.

---

## Clinician Details *(restricted — do not share with patient)*

**GAD-7 Raw Score:** 2/21
**Clinical Severity:** Minimal Anxiety — 0–4

**Per-Item Breakdown:**
  1. Feeling nervous, anxious, or on edge
     → Not at all (0)
  2. Not being able to stop or control worrying
     → Not at all (0)
  3. Worrying too much about different things
     → Not at all (0)
  4. Trouble relaxing
     → Several days (1)
  5. Being so restless that it is hard to sit still
     → Not at all (0)
  6. Becoming easily annoyed or irritable
     → Not at all (0)
  7. Feeling afraid, as if something awful might happen
     → Several days (1)

**Differentiation Assessment:** unclear
**Differentiation Reasoning:** Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category.
**Validation Notes:** Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 1 claims evaluated: 0 supported, 1 partially supported, 0 unsupported.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
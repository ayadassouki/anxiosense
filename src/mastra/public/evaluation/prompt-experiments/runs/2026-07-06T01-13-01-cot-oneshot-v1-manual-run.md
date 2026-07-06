# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
I've been feeling anxious on and off for a few weeks now. Social situations feel harder than they used to — I'll be in the middle of a conversation and suddenly worry I'm saying something wrong. I've been avoiding some group settings to feel safer. I still function day-to-day but it takes more effort than it used to.

## GAD-7 Score
_Not provided for this run._

## Emotion Agent Output
```json
{
  "emotions": [
    "anxiety"
  ],
  "emotional_intensity": "moderate",
  "evidence_from_text": [
    "I've been feeling anxious on and off for a few weeks now.",
    "Social situations feel harder than they used to — I'll be in the middle of a conversation and suddenly worry I'm saying something wrong.",
    "I've been avoiding some group settings to feel safer."
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [
    "Excessive worry",
    "Avoidance"
  ],
  "evidence_from_text": [
    "I've been feeling anxious on and off for a few weeks now.",
    "I'll be in the middle of a conversation and suddenly worry I'm saying something wrong.",
    "I've been avoiding some group settings to feel safer."
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [
    "Social pressures"
  ],
  "life_domains": [
    "Social"
  ],
  "evidence_from_text": [
    "Social situations feel harder than they used to",
    "I'll be in the middle of a conversation and suddenly worry I'm saying something wrong",
    "I've been avoiding some group settings to feel safer"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "moderate",
  "reasoning": "The user describes several anxiety-related experiences, such as worry during social situations and avoidance of group settings. While there is no explicit functional impairment mentioned, the need for increased effort in day-to-day functioning suggests some impact.",
  "recommended_support": "Consider a non-urgent appointment with a qualified healthcare professional if symptoms continue or affect daily functioning.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783300343933",
  "claims": [
    {
      "claimId": "EMO-1",
      "sourceAgent": "emotion",
      "claimText": "anxiety",
      "category": "emotional_state"
    },
    {
      "claimId": "SYM-1",
      "sourceAgent": "symptom",
      "claimText": "Excessive worry",
      "category": "anxiety_indicator"
    },
    {
      "claimId": "SYM-2",
      "sourceAgent": "symptom",
      "claimText": "Avoidance",
      "category": "anxiety_indicator"
    },
    {
      "claimId": "CTX-1",
      "sourceAgent": "context",
      "claimText": "Social pressures",
      "category": "contextual_stressor"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783300343933",
  "results": [
    {
      "claimId": "EMO-1",
      "claimText": "anxiety",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "DIFF-001",
          "text": "CHUNK_ID: DIFF-001\nSECTION: Features More Strongly Associated With Anxiety\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Autonomic/physical arousal: racing heart, sweating, trembling,\n  gastrointestinal discomfort.\n- Future-oriented cognitive content: worry, apprehension, catastrophic\n  anticipation of events that have not happened yet.\n- Specific behavioural avoidance tied to identifiable triggers or\n  situations.\n- Initial insomnia (difficulty falling asleep due to racing thoughts).\n- Muscle tension and motor restlessness rather than slowing.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.7155546247959137
        },
        {
          "chunkId": "ANX-002",
          "text": "CHUNK_ID: ANX-002\nINDICATOR: Autonomic / Sympathetic Over-Activity\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Physical symptoms driven by sympathetic nervous system\nactivation, including a racing or pounding heart, sweating, trembling,\ndry mouth, dizziness, or gastrointestinal discomfort, often occurring\nalongside anxious thoughts.\nPLAIN_LANGUAGE_EXAMPLES: \"My heart starts pounding for no clear reason.\"\n\"I get dizzy and sweaty when I think about it.\"\nNON_DIAGNOSTIC_NOTE: These physical sensations have many possible causes,\nincluding medical conditions unrelated to anxiety. Persistent or severe\nphysical symptoms warrant evaluation by a physician, not assumption that\nanxiety is the cause.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6923204660415649
        },
        {
          "chunkId": "ANX-001",
          "text": "CHUNK_ID: ANX-001\nINDICATOR: Excessive Worry / Apprehensive Expectation\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked symptoms of anxiety persisting for at least several\nmonths, occurring more days than not, manifested as either general\napprehension (\"free-floating anxiety\") or excessive worry focused on\nmultiple everyday events — most often concerning family, health, finances,\nschool, or work.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't stop worrying about things that probably\nwon't even happen.\" \"My mind keeps jumping to worst-case scenarios about\nschool or money.\"\nNON_DIAGNOSTIC_NOTE: Occasional worry about real stressors is common and\nexpected. This indicator describes worry that is pervasive across multiple\nlife areas and persists over months, not situational concern about a single\nupcoming event.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6843671798706055
        },
        {
          "chunkId": "DEP-005",
          "text": "CHUNK_ID: DEP-005\nINDICATOR: Difficulty Concentrating (Depression Presentation)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty concentrating or making decisions, often described\nalongside mental slowing or low motivation rather than active worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't make even small decisions anymore.\" \"My\nthinking feels slow and foggy.\"\nNON_DIAGNOSTIC_NOTE: Compare to ANX-004 in anxiety_indicators.txt — the\nunderlying mechanism (worry-driven vs. energy/motivation-driven) differs\neven though the surface symptom looks similar. See shared_symptoms.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6587068140506744
        }
      ]
    },
    {
      "claimId": "SYM-1",
      "claimText": "Excessive worry",
      "sourceAgent": "symptom",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "ANX-001",
          "text": "CHUNK_ID: ANX-001\nINDICATOR: Excessive Worry / Apprehensive Expectation\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked symptoms of anxiety persisting for at least several\nmonths, occurring more days than not, manifested as either general\napprehension (\"free-floating anxiety\") or excessive worry focused on\nmultiple everyday events — most often concerning family, health, finances,\nschool, or work.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't stop worrying about things that probably\nwon't even happen.\" \"My mind keeps jumping to worst-case scenarios about\nschool or money.\"\nNON_DIAGNOSTIC_NOTE: Occasional worry about real stressors is common and\nexpected. This indicator describes worry that is pervasive across multiple\nlife areas and persists over months, not situational concern about a single\nupcoming event.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.7836452722549438
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6741437315940857
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.6491518914699554
        },
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.599945604801178
        }
      ]
    },
    {
      "claimId": "SYM-2",
      "claimText": "Avoidance",
      "sourceAgent": "symptom",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "ANX-007",
          "text": "CHUNK_ID: ANX-007\nINDICATOR: Behavioural Avoidance\nSOURCE: ICD-11, WHO (2025-01), anxiety/fear-related disorders group\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Active avoidance of situations, places, people, or thoughts\nthat trigger anxiety or fear, to a degree that restricts daily functioning\n(e.g., avoiding classes, social events, or specific places).\nPLAIN_LANGUAGE_EXAMPLES: \"I've stopped going to lectures because I can't\nhandle being around that many people.\" \"I avoid speaking up in meetings.\"\nNON_DIAGNOSTIC_NOTE: Useful for assessing functional impairment and\nrelevant to referral_guidelines.txt tiering; avoidance of one specific,\nidentifiable trigger differs from pervasive avoidance across many contexts.",
          "source": "ICD-11, WHO (2025-01), anxiety/fear-related disorders group",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6906387805938721
        },
        {
          "chunkId": "ANX-001",
          "text": "CHUNK_ID: ANX-001\nINDICATOR: Excessive Worry / Apprehensive Expectation\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked symptoms of anxiety persisting for at least several\nmonths, occurring more days than not, manifested as either general\napprehension (\"free-floating anxiety\") or excessive worry focused on\nmultiple everyday events — most often concerning family, health, finances,\nschool, or work.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't stop worrying about things that probably\nwon't even happen.\" \"My mind keeps jumping to worst-case scenarios about\nschool or money.\"\nNON_DIAGNOSTIC_NOTE: Occasional worry about real stressors is common and\nexpected. This indicator describes worry that is pervasive across multiple\nlife areas and persists over months, not situational concern about a single\nupcoming event.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6138726472854614
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5642111599445343
        },
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5271600186824799
        }
      ]
    },
    {
      "claimId": "CTX-1",
      "claimText": "Social pressures",
      "sourceAgent": "context",
      "category": "contextual_stressor",
      "retrievedChunks": [
        {
          "chunkId": "CTX-009",
          "text": "CHUNK_ID: CTX-009\nSTRESSOR: Social Pressure and Peer Expectations\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Stress arising from the perceived need to meet social\nexpectations, fit in, or perform to the standards of peers, social groups,\nor online communities. Includes fear of judgment, exclusion, comparison to\nothers on social media, and the pressure to project a certain image.\nKEYWORDS: fitting in, judged, comparison, social media, peers, left out,\nexcluded, group, popularity, image, impression, what others think, embarrassed",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.7618133425712585
        },
        {
          "chunkId": "CTX-004",
          "text": "CHUNK_ID: CTX-004\nSTRESSOR: Family Stress\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Conflict, high expectations, or lack of support within the\nfamily or household.\nKEYWORDS: parents, family, expectations, arguments at home, mom, dad",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.6522742211818695
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 4,
    "totalChunksRetrieved": 14,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt",
      "instrument_reference.txt",
      "contextual_stressors.txt"
    ]
  },
  "riskLevel": "moderate"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783300343933",
  "claimValidations": [
    {
      "claimId": "EMO-1",
      "claimText": "anxiety",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "DIFF-001",
        "ANX-002"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.716, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_vs_depression.txt, anxiety_indicators.txt."
    },
    {
      "claimId": "SYM-1",
      "claimText": "Excessive worry",
      "sourceAgent": "symptom",
      "supportStatus": "supported",
      "citedChunkIds": [
        "ANX-001",
        "ANX-004"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.784, threshold: 0.72). Evidence retrieved from: anxiety_indicators.txt, anxiety_indicators.txt."
    },
    {
      "claimId": "SYM-2",
      "claimText": "Avoidance",
      "sourceAgent": "symptom",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-007",
        "ANX-001"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.691, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_indicators.txt."
    },
    {
      "claimId": "CTX-1",
      "claimText": "Social pressures",
      "sourceAgent": "context",
      "supportStatus": "supported",
      "citedChunkIds": [
        "CTX-009",
        "CTX-004"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.762, threshold: 0.72). Evidence retrieved from: contextual_stressors.txt, contextual_stressors.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 4 claims evaluated: 2 supported, 2 partially supported, 0 unsupported.",
  "riskLevel": "moderate"
}
```

## Final Report
```md
 # AnxioSense Screening Support Report

## 1. Input Mode
The mode used was Journal / Self-Report.

## 2. Summary of Concern
Based on the information provided, the available text may suggest potential anxiety-related concerns, including excessive worry and avoidance behaviors.

## 3. Emotional Indicators
The available text suggests anxiety.

## 4. Anxiety-Related Indicators
- Excessive worry [strong evidence]
- Avoidance [partial evidence]

## 5. Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:
1. "MARKED SYMPTOMS OF ANXIETY PERSISTING FOR AT LEAST SIX MONTHS" (ICD-11 6B00, WHO (2025-01))
2. "STRESS ARISING FROM THE PERCEIVED NEED TO MEET SOCIAL EXPECTATIONS, FIT IN, OR PERFORM THEMSELVES APPROPRIATELY" (CTX-009)
3. "AUTONOMIC/PHYSIOLOGICAL AROUSAL: RACING HEART, SWEATING, TREMBLING, GASTROINTESTINAL SYMPTOMS" (DIFF-001, FEATURES MORE STRONGLY ASSOCIATED WITH ANXIETY)
4. "PHYSICAL SYMPTOMS DRIVEN BY SYMPATHETIC NERVOUS SYSTEM ACTIVITY" (ANX-002, ICD-11 6B00, WHO (2025-01))

## 6. Contextual Factors
Social pressures [strong evidence]

## 7. Referral and Safety Recommendation
Consider seeking the support of a mental health professional for further assessment and guidance.

## 8. Limitations
This report is based only on the information provided. Missing context may affect interpretation, as this is not a clinical diagnosis. A qualified healthcare professional is needed for a comprehensive assessment. This report is intended for screening support only and should not be considered a clinical diagnosis. It is based solely on the information provided. If these experiences persist, worsen, or significantly affect daily life, consider speaking with a qualified healthcare professional for a comprehensive assessment.
```
# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
Title: Does anyone else feel like they can never stop worrying?
I'm a 21-year-old university student and I feel like my brain never shuts off. Even when nothing is actually wrong, I'm constantly thinking about what could go wrong next. I'll finish one assignment and immediately start stressing about the next one. Lately I've been having trouble sleeping because I keep replaying conversations in my head and wondering if I said something stupid. My friends tell me I'm overthinking but I genuinely can't stop. Is this just normal student stress or is something else going on?

## GAD-7 Score
_Not provided for this run._

## Emotion Agent Output
```json
{
  "emotions": [
    "anxiety",
    "stress"
  ],
  "emotional_intensity": "moderate",
  "evidence_from_text": [
    "I'm a 21-year-old university student and I feel like my brain never shuts off. Even when nothing is actually wrong, I'm constantly thinking about what could go wrong next.",
    "I'll finish one assignment and immediately start stressing about the next one",
    "Lately I've been having trouble sleeping because I keep replaying conversations in my head and wondering if I said something stupid"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [
    "Excessive worry",
    "Sleep disruption"
  ],
  "evidence_from_text": [
    "I'm constantly thinking about what could go wrong next",
    "Lately I've been having trouble sleeping because I keep replaying conversations in my head and wondering if I said something stupid"
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [
    "Academic stress"
  ],
  "life_domains": [
    "Academic"
  ],
  "evidence_from_text": [
    "I'm a 21-year-old university student",
    "even when nothing is actually wrong, I'm constantly thinking about what could go wrong next.",
    "I'll finish one assignment and immediately start stressing about the next one."
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "moderate",
  "reasoning": "The user describes persistent uncontrollable worry, sleep difficulty, and repeated self-criticism, suggesting several anxiety-related experiences that appear to affect their daily functioning.",
  "recommended_support": "Consider a non-urgent appointment with a qualified healthcare professional if symptoms continue or affect daily functioning.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783348404659",
  "claims": [
    {
      "claimId": "EMO-1",
      "sourceAgent": "emotion",
      "claimText": "anxiety",
      "category": "emotional_state"
    },
    {
      "claimId": "EMO-2",
      "sourceAgent": "emotion",
      "claimText": "stress",
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
      "claimText": "Sleep disruption",
      "category": "shared_symptom"
    },
    {
      "claimId": "CTX-1",
      "sourceAgent": "context",
      "claimText": "Academic stress",
      "category": "contextual_stressor"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783348404659",
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
      "claimId": "EMO-2",
      "claimText": "stress",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6776684522628784
        },
        {
          "chunkId": "DIFF-001",
          "text": "CHUNK_ID: DIFF-001\nSECTION: Features More Strongly Associated With Anxiety\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Autonomic/physical arousal: racing heart, sweating, trembling,\n  gastrointestinal discomfort.\n- Future-oriented cognitive content: worry, apprehension, catastrophic\n  anticipation of events that have not happened yet.\n- Specific behavioural avoidance tied to identifiable triggers or\n  situations.\n- Initial insomnia (difficulty falling asleep due to racing thoughts).\n- Muscle tension and motor restlessness rather than slowing.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6761362254619598
        },
        {
          "chunkId": "DEP-005",
          "text": "CHUNK_ID: DEP-005\nINDICATOR: Difficulty Concentrating (Depression Presentation)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty concentrating or making decisions, often described\nalongside mental slowing or low motivation rather than active worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't make even small decisions anymore.\" \"My\nthinking feels slow and foggy.\"\nNON_DIAGNOSTIC_NOTE: Compare to ANX-004 in anxiety_indicators.txt — the\nunderlying mechanism (worry-driven vs. energy/motivation-driven) differs\neven though the surface symptom looks similar. See shared_symptoms.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.6707468926906586
        },
        {
          "chunkId": "ANX-002",
          "text": "CHUNK_ID: ANX-002\nINDICATOR: Autonomic / Sympathetic Over-Activity\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Physical symptoms driven by sympathetic nervous system\nactivation, including a racing or pounding heart, sweating, trembling,\ndry mouth, dizziness, or gastrointestinal discomfort, often occurring\nalongside anxious thoughts.\nPLAIN_LANGUAGE_EXAMPLES: \"My heart starts pounding for no clear reason.\"\n\"I get dizzy and sweaty when I think about it.\"\nNON_DIAGNOSTIC_NOTE: These physical sensations have many possible causes,\nincluding medical conditions unrelated to anxiety. Persistent or severe\nphysical symptoms warrant evaluation by a physician, not assumption that\nanxiety is the cause.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6653009653091431
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
      "claimText": "Sleep disruption",
      "sourceAgent": "symptom",
      "category": "shared_symptom",
      "retrievedChunks": [
        {
          "chunkId": "SHARED-001",
          "text": "CHUNK_ID: SHARED-001\nSYMPTOM: Sleep Disturbance\nSOURCE_TYPE: differentiation_guidance\nDESCRIPTION: Disruption to normal sleep, present in both anxiety and\ndepressive presentations.\nANXIETY_PRESENTATION: Typically initial insomnia — difficulty falling\nasleep due to racing thoughts or worry at bedtime.\nDEPRESSION_PRESENTATION: Typically early-morning waking (terminal\ninsomnia) or hypersomnia (sleeping excessively, still feeling unrested).\nRETRIEVAL_NOTE: When a claim mentions sleep disturbance, retrieve this\nchunk and check which sub-pattern (onset vs. early-waking vs. hypersomnia)\nthe user described, if specified.",
          "sourceType": "differentiation_guidance",
          "file": "shared_symptoms.txt",
          "similarityScore": 0.7370824813842773
        },
        {
          "chunkId": "DIFF-001",
          "text": "CHUNK_ID: DIFF-001\nSECTION: Features More Strongly Associated With Anxiety\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Autonomic/physical arousal: racing heart, sweating, trembling,\n  gastrointestinal discomfort.\n- Future-oriented cognitive content: worry, apprehension, catastrophic\n  anticipation of events that have not happened yet.\n- Specific behavioural avoidance tied to identifiable triggers or\n  situations.\n- Initial insomnia (difficulty falling asleep due to racing thoughts).\n- Muscle tension and motor restlessness rather than slowing.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6626295745372772
        },
        {
          "chunkId": "SHARED-004",
          "text": "CHUNK_ID: SHARED-004\nSYMPTOM: Fatigue / Low Energy\nSOURCE_TYPE: differentiation_guidance\nDESCRIPTION: Reduced energy or persistent tiredness, common to both\ncategories and to many non-psychiatric conditions.\nANXIETY_PRESENTATION: Often described as \"wired but tired\" — exhausted yet\nunable to relax or switch off.\nDEPRESSION_PRESENTATION: Often described as heavy, flat fatigue without\nthe accompanying restlessness — low drive rather than restless exhaustion.\nRETRIEVAL_NOTE: Fatigue alone is a weak discriminator; always pair with\nat least one more specific indicator (e.g., anhedonia for depression,\nautonomic arousal for anxiety) before drawing any differentiation\nconclusion.",
          "sourceType": "differentiation_guidance",
          "file": "shared_symptoms.txt",
          "similarityScore": 0.6528882682323456
        },
        {
          "chunkId": "DIFF-004",
          "text": "CHUNK_ID: DIFF-004\nSECTION: Difficult Differentiation Situations\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Mixed Depressive and Anxiety Presentation: ICD-11 explicitly recognises\n  presentations where both anxious and depressive symptoms are present\n  together without either independently reaching a full, distinct\n  threshold. When a user's claims include clear signals from both\n  DIFF-001 and DIFF-002, the appropriate output is \"mixed\" — not a forced\n  choice between the two.\n- Agitated Depression: Severe psychomotor agitation, pacing, or racing\n  thoughts can occur within a depressive presentation and closely\n  resemble acute anxiety. Presence of agitation alone should not\n  automatically be coded as an anxiety signal if clear depressive features\n  (anhedonia, hopelessness) dominate.\n- Chronic Anxiety Exhaustion: Long-standing anxiety can lead to secondary\n  fatigue, withdrawal, and low mood that superficially resembles primary\n  depression. Consider the apparent sequence the user describes (e.g.,\n  \"I've been anxious for months and now I just feel drained\") as\n  contextual information, not as proof of either category.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6060601770877838
        }
      ]
    },
    {
      "claimId": "CTX-1",
      "claimText": "Academic stress",
      "sourceAgent": "context",
      "category": "contextual_stressor",
      "retrievedChunks": [
        {
          "chunkId": "CTX-001",
          "text": "CHUNK_ID: CTX-001\nSTRESSOR: Academic Stress\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Stress related to exams, grades, workload, performance\nexpectations, or fear of academic failure.\nKEYWORDS: exam, grades, GPA, assignment, workload, deadline, failing,\nuniversity, class",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.8097085356712341
        },
        {
          "chunkId": "CTX-002",
          "text": "CHUNK_ID: CTX-002\nSTRESSOR: Financial Stress\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Difficulty meeting basic living costs, debt, tuition\npressure, or general financial insecurity.\nKEYWORDS: rent, debt, tuition, bills, money, broke, financial aid",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.7304998934268951
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 5,
    "totalChunksRetrieved": 18,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt",
      "instrument_reference.txt",
      "shared_symptoms.txt",
      "contextual_stressors.txt"
    ]
  },
  "riskLevel": "moderate"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783348404659",
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
      "claimId": "EMO-2",
      "claimText": "stress",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-004",
        "DIFF-001"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.678, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_vs_depression.txt."
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
      "claimText": "Sleep disruption",
      "sourceAgent": "symptom",
      "supportStatus": "supported",
      "citedChunkIds": [
        "SHARED-001",
        "DIFF-001"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.737, threshold: 0.72). Evidence retrieved from: shared_symptoms.txt, anxiety_vs_depression.txt."
    },
    {
      "claimId": "CTX-1",
      "claimText": "Academic stress",
      "sourceAgent": "context",
      "supportStatus": "supported",
      "citedChunkIds": [
        "CTX-001",
        "CTX-002"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.810, threshold: 0.72). Evidence retrieved from: contextual_stressors.txt, contextual_stressors.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 5 claims evaluated: 3 supported, 2 partially supported, 0 unsupported.",
  "riskLevel": "moderate"
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
- Persistent worry
- Sleep disruption
- Academic stress
These findings were checked against the clinical guidance and screening knowledge base used by AnxioSense.

## Recommendation
Given these findings, it may be beneficial to discuss your concerns with a qualified healthcare professional who can provide a comprehensive assessment and appropriate guidance for managing stress and anxiety.

## Evidence Agreement

**High** — The identified indicators were broadly consistent with the clinical guidance used.

## Limitations
This report is based solely on the information provided within the context of a social media post. Missing context may affect interpretation, and this should not be considered a clinical diagnosis. A qualified healthcare professional is needed for a full clinical assessment to determine any underlying issues and provide appropriate treatment options. It is important to note that analyzing social media text adds additional uncertainty to the analysis due to factors such as tone and intent. This report is intended for screening support only and should not be considered a clinical diagnosis.

---

## Clinician Summary *(restricted — do not share with patient)*

**Validated Indicators:**
  - anxiety (Partially Supported)
  - stress (Partially Supported)
  - Excessive worry (Supported)
  - Sleep disruption (Supported)
  - Academic stress (Supported)

**Evidence Confidence:** High

**Differential Considerations:**
Available information was insufficient to confidently distinguish anxiety-related symptoms from other possible conditions such as depression. Further clinical assessment would be required.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
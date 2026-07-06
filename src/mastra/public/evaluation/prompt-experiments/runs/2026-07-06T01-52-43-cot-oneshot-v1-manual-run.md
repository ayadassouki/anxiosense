# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
Lately I've been finding it harder to switch off after work. I keep going over conversations in my head wondering if I said the right thing. I've been sleeping okay but some nights I lie awake for a while. I wouldn't say it's ruining my life, but it's there in the background.

## GAD-7 Score
GAD-7 Self-Report Screening

Based on the information provided, the system identifies a pattern of anxiety-related experiences and interpreted as;

**Mild Concern Pattern**

Your responses indicate the presence of some anxiety-related experiences. While these feelings may not currently be causing substantial difficulties, monitoring how they change over time may be helpful. Consider using healthy coping strategies and seeking support if symptoms become more frequent or distressing.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Several days
  2. Not being able to stop or control worrying
     → Several days
  3. Worrying too much about different things
     → More than half the days
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → Not at all
  6. Becoming easily annoyed or irritable
     → Several days
  7. Feeling afraid, as if something awful might happen
     → Several days

This result is intended for screening purposes only and should not be considered a diagnosis.

## Emotion Agent Output
```json
{
  "emotions": [
    "anxiety"
  ],
  "emotional_intensity": "moderate",
  "evidence_from_text": [
    "I keep going over conversations in my head wondering if I said the right thing.",
    "I've been sleeping okay but some nights I lie awake for a while"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [
    "Excessive worry"
  ],
  "evidence_from_text": [
    "I keep going over conversations in my head wondering if I said the right thing",
    "I wouldn't say it's ruining my life, but it's there in the background"
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{
  "contextual_stressors": [
    "Work stress"
  ],
  "life_domains": [
    "Work"
  ],
  "evidence_from_text": [
    "I've been finding it harder to switch off after work",
    "I keep going over conversations in my head wondering if I said the right thing"
  ]
}
```

## Referral Agent Output
```json
{
  "risk_level": "low",
  "reasoning": "The user describes trouble relaxing after work and occasional difficulty sleeping, suggesting some anxiety-related experiences. However, these seem to be mild and do not appear to significantly affect daily functioning or cause an immediate safety concern.",
  "recommended_support": "If symptoms persist or worsen, consider monitoring and optional follow-up with a qualified healthcare professional.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783302738040",
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
      "claimId": "CTX-1",
      "sourceAgent": "context",
      "claimText": "Work stress",
      "category": "contextual_stressor"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783302738040",
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
      "claimId": "CTX-1",
      "claimText": "Work stress",
      "sourceAgent": "context",
      "category": "contextual_stressor",
      "retrievedChunks": [
        {
          "chunkId": "CTX-008",
          "text": "CHUNK_ID: CTX-008\nSTRESSOR: Occupational and Workplace Stress\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Stress arising from job demands, difficult colleagues or\nmanagers, fear of being fired or laid off, workplace conflict, long hours,\npoor work-life balance, or feeling undervalued or overwhelmed in a work\nenvironment. Relevant for employed students, part-time workers, or early-career\nprofessionals.\nKEYWORDS: work, boss, manager, coworker, shift, fired, layoff, overtime,\nworkplace, job stress, office, hours, deadline at work, undervalued, burned out",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.7894014269113541
        },
        {
          "chunkId": "CTX-005",
          "text": "CHUNK_ID: CTX-005\nSTRESSOR: Career Uncertainty\nSOURCE_TYPE: contextual_taxonomy\nDESCRIPTION: Anxiety or stress related to job searching, graduation\ntransitions, or ambiguity about future career direction.\nKEYWORDS: graduation, job hunt, unemployed, rejection, resume, internship",
          "sourceType": "contextual_taxonomy",
          "file": "contextual_stressors.txt",
          "similarityScore": 0.7494894862174988
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 3,
    "totalChunksRetrieved": 10,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt",
      "instrument_reference.txt",
      "contextual_stressors.txt"
    ]
  },
  "riskLevel": "low"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783302738040",
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
      "claimId": "CTX-1",
      "claimText": "Work stress",
      "sourceAgent": "context",
      "supportStatus": "supported",
      "citedChunkIds": [
        "CTX-008",
        "CTX-005"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.789, threshold: 0.72). Evidence retrieved from: contextual_stressors.txt, contextual_stressors.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 3 claims evaluated: 2 supported, 1 partially supported, 0 unsupported.",
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

**Mild Concern Pattern**

Your responses indicate the presence of some anxiety-related experiences. While these feelings may not currently be causing substantial difficulties, monitoring how they change over time may be helpful. Consider using healthy coping strategies and seeking support if symptoms become more frequent or distressing.

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → Several days
  2. Not being able to stop or control worrying
     → Several days
  3. Worrying too much about different things
     → More than half the days
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → Not at all
  6. Becoming easily annoyed or irritable
     → Several days
  7. Feeling afraid, as if something awful might happen
     → Several days

This result is intended for screening purposes only and should not be considered a diagnosis.

## Emotional Indicators
The available text suggests anxiety may be present.

## Anxiety-Related Indicators
Excessive worry is evident in the provided information.

## Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:
1. "STRESSOR: Occupational and Workplace Stress
SOURCE_TYPE: contextual_taxonomy
DESCRIPTION: Stress arising from job demands, difficult colleagues or managers, fear of being fired or layoffs..."
2. "INDICATOR: Excessive Worry / Apprehensive Expectation
SOURCE: ICD-11 6B00, WHO (2025-01)
SOURCE_TYPE: clinical_description
DESCRIPTION: Marked symptoms of anxiety persisting for at least six months..."
3. "STRESSOR: Career Uncertainty
SOURCE_TYPE: contextual_taxonomy
DESCRIPTION: Anxiety or stress related to job searching, graduation transitions, or ambiguity about future career direction..."
4. "SECTION: Features More Strongly Associated With Anxiety
SOURCE_TYPE: differentiation_guidance
CONTENT: - Autonomic/physical arousal: racing heart, sweating, trembling, gastrointestinal upset..."

## Contextual Factors
Work stress and career uncertainty are present in the context.

## Recommendation
Monitoring how these experiences change over time may be helpful. Consider speaking with a healthcare professional if they become more frequent, worsen, or begin affecting daily functioning.

## Evidence Agreement

**High** — The structured questionnaire and written text indicators were largely consistent with the clinical knowledge base.

## Limitations
This report is based solely on the information provided. Missing context may affect interpretation. This report is intended for screening support only and should not be considered a clinical diagnosis. A qualified healthcare professional is needed for a comprehensive assessment if these experiences persist, worsen, or significantly affect daily life.

---

## Clinician Details *(restricted — do not share with patient)*

**GAD-7 Raw Score:** 7/21
**Clinical Severity:** Mild Anxiety — 5–9

**Per-Item Breakdown:**
  1. Feeling nervous, anxious, or on edge
     → Several days (1)
  2. Not being able to stop or control worrying
     → Several days (1)
  3. Worrying too much about different things
     → More than half the days (2)
  4. Trouble relaxing
     → Several days (1)
  5. Being so restless that it is hard to sit still
     → Not at all (0)
  6. Becoming easily annoyed or irritable
     → Several days (1)
  7. Feeling afraid, as if something awful might happen
     → Several days (1)

**Differentiation Assessment:** unclear
**Differentiation Reasoning:** Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category.
**Validation Notes:** Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 3 claims evaluated: 2 supported, 1 partially supported, 0 unsupported.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
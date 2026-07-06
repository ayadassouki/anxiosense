# AnxioSense Workflow Run

## Test Case
manual-run

## Prompt Version
cot-oneshot-v1

## User Input
Over the past several months, my anxiety has become overwhelming. I wake up every morning already feeling tense, and my mind immediately starts racing about everything that could go wrong during the day.

I constantly worry about university, money, my family, and my future, even when nothing is actually happening. I can't control the worrying, no matter how hard I try.

I've been sleeping only a few hours each night because I can't stop thinking. During lectures I can't focus because my mind keeps jumping from one worry to another. I've missed assignment deadlines because I spend hours checking and rechecking my work, afraid I'll make a mistake.

I've stopped seeing my friends because I feel exhausted and overwhelmed. My family has noticed that I'm becoming more irritable, and even small things make me panic. My heart races, my muscles are tense all the time, and I feel like something terrible is about to happen almost every day.

This has been affecting my grades, my relationships, and my daily life for months. I know this isn't just normal stress anymore, and I think I need professional help because I don't feel like I can manage it on my own.

## GAD-7 Score
GAD-7 Self-Report Screening
Concern Pattern: Elevated Concern Pattern

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → More than half the days
  2. Not being able to stop or control worrying
     → More than half the days
  3. Worrying too much about different things
     → More than half the days
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → More than half the days
  6. Becoming easily annoyed or irritable
     → More than half the days
  7. Feeling afraid, as if something awful might happen
     → Nearly every day

Your responses suggest several experiences that are commonly associated with anxiety and may be affecting your well-being. It may be beneficial to discuss these concerns with a healthcare professional who can provide a more comprehensive assessment and appropriate guidance.

Note: The GAD-7 is a validated self-report screening instrument used 
as an internal reference. It is not a diagnostic tool. This result 
should not be considered a clinical assessment. If you have concerns 
about your mental health, please speak with a qualified healthcare professional.

## Emotion Agent Output
```json
{
  "emotions": [
    "anxiety",
    "stress",
    "frustration",
    "fear"
  ],
  "emotional_intensity": "high",
  "evidence_from_text": [
    "my anxiety has become overwhelming",
    "I wake up every morning already feeling tense",
    "my mind immediately starts racing about everything that could go wrong during the day",
    "I constantly worry about university, money, my family, and my future",
    "even when nothing is actually happening",
    "I can't control the worrying",
    "I've been sleeping only a few hours each night because I can't stop thinking",
    "During lectures I can't focus because my mind keeps jumping from one worry to another",
    "I've missed assignment deadlines because I spend hours checking and rechecking my work, afraid I'll make a mistake",
    "I've stopped seeing my friends because I feel exhausted and overwhelmed",
    "My family has noticed that I'm becoming more irritable",
    "even small things make me panic",
    "My heart races, my muscles are tense all the time",
    "I feel like something terrible is about to happen almost every day"
  ]
}
```

## Symptom Agent Output
```json
{
  "possible_anxiety_indicators": [
    "Excessive worry",
    "Sleep disruption",
    "Concentration difficulty",
    "Restlessness",
    "Tension",
    "Functional impairment"
  ],
  "evidence_from_text": [
    "I wake up every morning already feeling tense",
    "my mind immediately starts racing about everything that could go wrong during the day",
    "I constantly worry about university, money, my family, and my future",
    "I can't control the worrying, no matter how hard I try",
    "I've been sleeping only a few hours each night because I can't stop thinking",
    "During lectures I can't focus because my mind keeps jumping from one worry to another",
    "I've missed assignment deadlines because I spend hours checking and rechecking my work, afraid I'll make a mistake",
    "I've stopped seeing my friends because I feel exhausted and overwhelmed",
    "My family has noticed that I'm becoming more irritable",
    "even small things make me panic",
    "My heart races",
    "my muscles are tense all the time",
    "I feel like something terrible is about to happen almost every day",
    "This has been affecting my grades, my relationships, and my daily life for months"
  ],
  "not_enough_information": false
}
```

## Context Agent Output
```json
{"contextual_stressors":["Academic stress","Financial stress","Family stress","Life-transition stress","Social pressures"],"life_domains":["Academic","Finance","Family","Life Transitions","Social"],"evidence_from_text":["I can't control the worrying, no matter how hard I try. (Academic stress)","I constantly worry about university, money, my family, and my future. (Financial stress, Family stress, Life-transition stress)","I've missed assignment deadlines because I spend hours checking and rechecking my work. (Academic stress)","During lectures I can't focus because my mind keeps jumping from one worry to another. (Academic stress)","I've stopped seeing my friends because I feel exhausted and overwhelmed. (Social pressures)"}]
```

## Referral Agent Output
```json
{
  "risk_level": "moderate",
  "reasoning": "The user describes persistent uncontrollable worry, sleep difficulty, concentration difficulty, avoidance (stopping seeing friends), and functional impact (affecting grades, relationships, daily life). This suggests several anxiety-related experiences with significant functional impairment.",
  "recommended_support": "Consider a non-urgent appointment with a qualified healthcare professional if symptoms continue or affect daily functioning.",
  "safety_note": ""
}
```

## Build Claims Step
```json
{
  "sessionId": "session-1783281753631",
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
      "claimId": "EMO-3",
      "sourceAgent": "emotion",
      "claimText": "frustration",
      "category": "emotional_state"
    },
    {
      "claimId": "EMO-4",
      "sourceAgent": "emotion",
      "claimText": "fear",
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
      "claimId": "SYM-3",
      "sourceAgent": "symptom",
      "claimText": "Concentration difficulty",
      "category": "shared_symptom"
    },
    {
      "claimId": "SYM-4",
      "sourceAgent": "symptom",
      "claimText": "Restlessness",
      "category": "anxiety_indicator"
    },
    {
      "claimId": "SYM-5",
      "sourceAgent": "symptom",
      "claimText": "Tension",
      "category": "anxiety_indicator"
    },
    {
      "claimId": "SYM-6",
      "sourceAgent": "symptom",
      "claimText": "Functional impairment",
      "category": "anxiety_indicator"
    }
  ]
}
```

## Retrieval Step
```json
{
  "sessionId": "session-1783281753631",
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
      "claimId": "EMO-3",
      "claimText": "frustration",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "ANX-005",
          "text": "CHUNK_ID: ANX-005\nINDICATOR: Irritability (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Low frustration tolerance or a persistent edgy, on-edge mood,\ncommonly arising from chronic nervous system activation and the strain of\nongoing worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I snap at people more than I used to.\" \"Small\nthings set me off lately.\"\nNON_DIAGNOSTIC_NOTE: Irritability is a non-specific symptom shared with\ndepression (see shared_symptoms.txt) and many other states, including\nordinary stress and sleep deprivation.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6153232455253601
        },
        {
          "chunkId": "DEP-004",
          "text": "CHUNK_ID: DEP-004\nINDICATOR: Feelings of Worthlessness or Excessive Guilt\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Persistent feelings of worthlessness, or excessive or\ninappropriate guilt, extending beyond reasonable self-criticism about a\nspecific event.\nPLAIN_LANGUAGE_EXAMPLES: \"I feel like a burden to everyone around me.\"\n\"Everything that goes wrong feels like it's my fault, even when it\nisn't.\"\nNON_DIAGNOSTIC_NOTE: Relevant to referral_guidelines.txt severity tiering.\nProfound hopelessness combined with this indicator should be cross-checked\nagainst safety_boundary.txt escalation criteria.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5825001001358032
        },
        {
          "chunkId": "DEP-007",
          "text": "CHUNK_ID: DEP-007\nINDICATOR: Psychomotor Agitation or Retardation\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Observable slowing of movement and speech (retardation), or\nits opposite, restless agitation, occurring alongside other depressive\nfeatures.\nPLAIN_LANGUAGE_EXAMPLES: \"I feel like I'm moving in slow motion.\" /\n\"I can't stop pacing, even though I feel exhausted.\"\nNON_DIAGNOSTIC_NOTE: Agitated presentations of depression can closely\nresemble anxiety. See anxiety_vs_depression.txt, \"Difficult\nDifferentiation Situations.\"",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5801929831504822
        },
        {
          "chunkId": "ANX-003",
          "text": "CHUNK_ID: ANX-003\nINDICATOR: Muscle Tension and Motor Restlessness\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Chronic muscular tension, an inability to relax, feeling\n\"keyed up\" or on edge, or motor restlessness such as pacing or fidgeting.\nPLAIN_LANGUAGE_EXAMPLES: \"My shoulders are always tight.\" \"I can't sit\nstill, I have to keep moving.\"\nNON_DIAGNOSTIC_NOTE: Differentiates generalized anxiety presentations from\npurely cognitive worry; physical tension alone is common and not, by\nitself, indicative of a disorder.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.5599940121173859
        }
      ]
    },
    {
      "claimId": "EMO-4",
      "claimText": "fear",
      "sourceAgent": "emotion",
      "category": "emotional_state",
      "retrievedChunks": [
        {
          "chunkId": "ANX-008",
          "text": "CHUNK_ID: ANX-008\nINDICATOR: Fear of Negative Social Evaluation\nSOURCE: ICD-11, WHO (2025-01), Social Anxiety Disorder (6B04)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked and persistent fear or anxiety about one or more social\nsituations in which the person may be scrutinised by others, driven by\nfear of negative evaluation, embarrassment, or rejection.\nPLAIN_LANGUAGE_EXAMPLES: \"I freeze up when I have to talk to people I don't\nknow well.\" \"I'm terrified of saying something stupid in front of others.\"\nNON_DIAGNOSTIC_NOTE: Distinguishing situational social discomfort (common\nand not pathological) from pervasive, impairing social fear requires\nprofessional assessment.",
          "source": "ICD-11, WHO (2025-01), Social Anxiety Disorder (6B04)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.628254622220993
        },
        {
          "chunkId": "DIFF-001",
          "text": "CHUNK_ID: DIFF-001\nSECTION: Features More Strongly Associated With Anxiety\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Autonomic/physical arousal: racing heart, sweating, trembling,\n  gastrointestinal discomfort.\n- Future-oriented cognitive content: worry, apprehension, catastrophic\n  anticipation of events that have not happened yet.\n- Specific behavioural avoidance tied to identifiable triggers or\n  situations.\n- Initial insomnia (difficulty falling asleep due to racing thoughts).\n- Muscle tension and motor restlessness rather than slowing.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6226788759231567
        },
        {
          "chunkId": "ANX-001",
          "text": "CHUNK_ID: ANX-001\nINDICATOR: Excessive Worry / Apprehensive Expectation\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Marked symptoms of anxiety persisting for at least several\nmonths, occurring more days than not, manifested as either general\napprehension (\"free-floating anxiety\") or excessive worry focused on\nmultiple everyday events — most often concerning family, health, finances,\nschool, or work.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't stop worrying about things that probably\nwon't even happen.\" \"My mind keeps jumping to worst-case scenarios about\nschool or money.\"\nNON_DIAGNOSTIC_NOTE: Occasional worry about real stressors is common and\nexpected. This indicator describes worry that is pervasive across multiple\nlife areas and persists over months, not situational concern about a single\nupcoming event.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.598040759563446
        },
        {
          "chunkId": "DEP-005",
          "text": "CHUNK_ID: DEP-005\nINDICATOR: Difficulty Concentrating (Depression Presentation)\nSOURCE: ICD-11 6A70, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty concentrating or making decisions, often described\nalongside mental slowing or low motivation rather than active worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I can't make even small decisions anymore.\" \"My\nthinking feels slow and foggy.\"\nNON_DIAGNOSTIC_NOTE: Compare to ANX-004 in anxiety_indicators.txt — the\nunderlying mechanism (worry-driven vs. energy/motivation-driven) differs\neven though the surface symptom looks similar. See shared_symptoms.txt.",
          "source": "ICD-11 6A70, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "depression_indicators.txt",
          "similarityScore": 0.5663962066173553
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
      "claimId": "SYM-3",
      "claimText": "Concentration difficulty",
      "sourceAgent": "symptom",
      "category": "shared_symptom",
      "retrievedChunks": [
        {
          "chunkId": "SHARED-002",
          "text": "CHUNK_ID: SHARED-002\nSYMPTOM: Concentration Difficulty\nSOURCE_TYPE: differentiation_guidance\nDESCRIPTION: Reduced ability to focus or make decisions, present in both\nanxiety and depressive presentations.\nANXIETY_PRESENTATION: Driven by attention being pulled toward worry or\nthreat-monitoring; the person is \"too busy thinking about problems\" to\nfocus.\nDEPRESSION_PRESENTATION: Driven by mental slowing, low motivation, or\nreduced cognitive energy; the person describes thinking as \"foggy\" or\n\"slow\" rather than \"distracted.\"\nRETRIEVAL_NOTE: The user's own description of *why* focus is difficult\n(worry vs. low energy/motivation) is the key differentiator here, more\nthan the symptom itself.",
          "sourceType": "differentiation_guidance",
          "file": "shared_symptoms.txt",
          "similarityScore": 0.7988869845867157
        },
        {
          "chunkId": "DIFF-004",
          "text": "CHUNK_ID: DIFF-004\nSECTION: Difficult Differentiation Situations\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Mixed Depressive and Anxiety Presentation: ICD-11 explicitly recognises\n  presentations where both anxious and depressive symptoms are present\n  together without either independently reaching a full, distinct\n  threshold. When a user's claims include clear signals from both\n  DIFF-001 and DIFF-002, the appropriate output is \"mixed\" — not a forced\n  choice between the two.\n- Agitated Depression: Severe psychomotor agitation, pacing, or racing\n  thoughts can occur within a depressive presentation and closely\n  resemble acute anxiety. Presence of agitation alone should not\n  automatically be coded as an anxiety signal if clear depressive features\n  (anhedonia, hopelessness) dominate.\n- Chronic Anxiety Exhaustion: Long-standing anxiety can lead to secondary\n  fatigue, withdrawal, and low mood that superficially resembles primary\n  depression. Consider the apparent sequence the user describes (e.g.,\n  \"I've been anxious for months and now I just feel drained\") as\n  contextual information, not as proof of either category.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6401714980602264
        },
        {
          "chunkId": "DIFF-003",
          "text": "CHUNK_ID: DIFF-003\nSECTION: Features Common to Both (Low Differentiating Value Alone)\nSOURCE_TYPE: differentiation_guidance\nCONTENT:\n- Fatigue or low energy.\n- Concentration or decision-making difficulty.\n- Irritability.\n- General distress and some degree of functional impairment.\nThese should not be used alone to assign a primary lean; always pair with\nat least one indicator from DIFF-001 or DIFF-002.",
          "sourceType": "differentiation_guidance",
          "file": "anxiety_vs_depression.txt",
          "similarityScore": 0.6225974261760712
        },
        {
          "chunkId": "SHARED-001",
          "text": "CHUNK_ID: SHARED-001\nSYMPTOM: Sleep Disturbance\nSOURCE_TYPE: differentiation_guidance\nDESCRIPTION: Disruption to normal sleep, present in both anxiety and\ndepressive presentations.\nANXIETY_PRESENTATION: Typically initial insomnia — difficulty falling\nasleep due to racing thoughts or worry at bedtime.\nDEPRESSION_PRESENTATION: Typically early-morning waking (terminal\ninsomnia) or hypersomnia (sleeping excessively, still feeling unrested).\nRETRIEVAL_NOTE: When a claim mentions sleep disturbance, retrieve this\nchunk and check which sub-pattern (onset vs. early-waking vs. hypersomnia)\nthe user described, if specified.",
          "sourceType": "differentiation_guidance",
          "file": "shared_symptoms.txt",
          "similarityScore": 0.6063150465488434
        }
      ]
    },
    {
      "claimId": "SYM-4",
      "claimText": "Restlessness",
      "sourceAgent": "symptom",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "ANX-003",
          "text": "CHUNK_ID: ANX-003\nINDICATOR: Muscle Tension and Motor Restlessness\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Chronic muscular tension, an inability to relax, feeling\n\"keyed up\" or on edge, or motor restlessness such as pacing or fidgeting.\nPLAIN_LANGUAGE_EXAMPLES: \"My shoulders are always tight.\" \"I can't sit\nstill, I have to keep moving.\"\nNON_DIAGNOSTIC_NOTE: Differentiates generalized anxiety presentations from\npurely cognitive worry; physical tension alone is common and not, by\nitself, indicative of a disorder.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.7143517434597015
        },
        {
          "chunkId": "ANX-005",
          "text": "CHUNK_ID: ANX-005\nINDICATOR: Irritability (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Low frustration tolerance or a persistent edgy, on-edge mood,\ncommonly arising from chronic nervous system activation and the strain of\nongoing worry.\nPLAIN_LANGUAGE_EXAMPLES: \"I snap at people more than I used to.\" \"Small\nthings set me off lately.\"\nNON_DIAGNOSTIC_NOTE: Irritability is a non-specific symptom shared with\ndepression (see shared_symptoms.txt) and many other states, including\nordinary stress and sleep deprivation.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6630297303199768
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.6567454934120178
        },
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5573848187923431
        }
      ]
    },
    {
      "claimId": "SYM-5",
      "claimText": "Tension",
      "sourceAgent": "symptom",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "ANX-003",
          "text": "CHUNK_ID: ANX-003\nINDICATOR: Muscle Tension and Motor Restlessness\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Chronic muscular tension, an inability to relax, feeling\n\"keyed up\" or on edge, or motor restlessness such as pacing or fidgeting.\nPLAIN_LANGUAGE_EXAMPLES: \"My shoulders are always tight.\" \"I can't sit\nstill, I have to keep moving.\"\nNON_DIAGNOSTIC_NOTE: Differentiates generalized anxiety presentations from\npurely cognitive worry; physical tension alone is common and not, by\nitself, indicative of a disorder.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.7007846236228943
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6047766506671906
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5533132553100586
        },
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5394822657108307
        }
      ]
    },
    {
      "claimId": "SYM-6",
      "claimText": "Functional impairment",
      "sourceAgent": "symptom",
      "category": "anxiety_indicator",
      "retrievedChunks": [
        {
          "chunkId": "ANX-007",
          "text": "CHUNK_ID: ANX-007\nINDICATOR: Behavioural Avoidance\nSOURCE: ICD-11, WHO (2025-01), anxiety/fear-related disorders group\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Active avoidance of situations, places, people, or thoughts\nthat trigger anxiety or fear, to a degree that restricts daily functioning\n(e.g., avoiding classes, social events, or specific places).\nPLAIN_LANGUAGE_EXAMPLES: \"I've stopped going to lectures because I can't\nhandle being around that many people.\" \"I avoid speaking up in meetings.\"\nNON_DIAGNOSTIC_NOTE: Useful for assessing functional impairment and\nrelevant to referral_guidelines.txt tiering; avoidance of one specific,\nidentifiable trigger differs from pervasive avoidance across many contexts.",
          "source": "ICD-11, WHO (2025-01), anxiety/fear-related disorders group",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6146388947963715
        },
        {
          "chunkId": "ANX-004",
          "text": "CHUNK_ID: ANX-004\nINDICATOR: Concentration Difficulty (Anxiety Presentation)\nSOURCE: ICD-11 6B00, WHO (2025-01)\nSOURCE_TYPE: clinical_description\nDESCRIPTION: Difficulty maintaining concentration, often because attention\nis repeatedly pulled toward worry, threat-monitoring, or anticipated\nproblems rather than the task at hand.\nPLAIN_LANGUAGE_EXAMPLES: \"I read the same paragraph five times because my\nmind keeps wandering to what could go wrong.\" \"I can't focus in class\nbecause I'm thinking about everything else.\"\nNON_DIAGNOSTIC_NOTE: See shared_symptoms.txt for how this differs in\npresentation from concentration difficulty associated with depression.",
          "source": "ICD-11 6B00, WHO (2025-01)",
          "sourceType": "clinical_description",
          "file": "anxiety_indicators.txt",
          "similarityScore": 0.6058832108974457
        },
        {
          "chunkId": "INST-GAD7-INTRO",
          "text": "CHUNK_ID: INST-GAD7-INTRO\nINSTRUMENT: GAD-7\nSOURCE_TYPE: validated_instrument_item\nCONTENT: Over the last two weeks, how often have you been bothered by the\nfollowing problems? Response options: Not at all (0), Several days (1),\nMore than half the days (2), Nearly every day (3).\nSCORING_NOTE: Total score range 0-21. Cutoffs: 5 = mild, 10 = moderate,\n15 = severe. A score of 10 or greater is the standard threshold suggesting\nfurther evaluation is warranted. AnxioSense does not apply this scoring\ndirectly to free-text input; included for reference only.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5937250554561615
        },
        {
          "chunkId": "INST-GAD7-01",
          "text": "CHUNK_ID: INST-GAD7-01\nINSTRUMENT: GAD-7\nITEM_NUMBER: 1\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling nervous, anxious, or on edge.\n\nCHUNK_ID: INST-GAD7-02\nINSTRUMENT: GAD-7\nITEM_NUMBER: 2\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Not being able to stop or control worrying.\n\nCHUNK_ID: INST-GAD7-03\nINSTRUMENT: GAD-7\nITEM_NUMBER: 3\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Worrying too much about different things.\n\nCHUNK_ID: INST-GAD7-04\nINSTRUMENT: GAD-7\nITEM_NUMBER: 4\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Trouble relaxing.\n\nCHUNK_ID: INST-GAD7-05\nINSTRUMENT: GAD-7\nITEM_NUMBER: 5\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Being so restless that it is hard to sit still.\n\nCHUNK_ID: INST-GAD7-06\nINSTRUMENT: GAD-7\nITEM_NUMBER: 6\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Becoming easily annoyed or irritable.\n\nCHUNK_ID: INST-GAD7-07\nINSTRUMENT: GAD-7\nITEM_NUMBER: 7\nSOURCE_TYPE: validated_instrument_item\nITEM_TEXT: Feeling afraid as if something awful might happen.",
          "sourceType": "validated_instrument_item",
          "file": "instrument_reference.txt",
          "similarityScore": 0.5806376934051514
        }
      ]
    }
  ],
  "sessionDifferentiationChunks": [],
  "retrievalMeta": {
    "totalClaims": 10,
    "totalChunksRetrieved": 40,
    "indexesQueried": [
      "anxiety_indicators.txt",
      "depression_indicators.txt",
      "anxiety_vs_depression.txt",
      "instrument_reference.txt",
      "shared_symptoms.txt"
    ]
  },
  "riskLevel": "moderate"
}
```

## Evidence Validation Step
```json
{
  "sessionId": "session-1783281753631",
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
      "claimId": "EMO-3",
      "claimText": "frustration",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-005",
        "DEP-004"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.615, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, depression_indicators.txt."
    },
    {
      "claimId": "EMO-4",
      "claimText": "fear",
      "sourceAgent": "emotion",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-008",
        "DIFF-001"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.628, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_vs_depression.txt."
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
      "claimId": "SYM-3",
      "claimText": "Concentration difficulty",
      "sourceAgent": "symptom",
      "supportStatus": "supported",
      "citedChunkIds": [
        "SHARED-002",
        "DIFF-004"
      ],
      "validationNote": "Claim is semantically supported by knowledge-base evidence (cosine similarity: 0.799, threshold: 0.72). Evidence retrieved from: shared_symptoms.txt, anxiety_vs_depression.txt."
    },
    {
      "claimId": "SYM-4",
      "claimText": "Restlessness",
      "sourceAgent": "symptom",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-003",
        "ANX-005"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.714, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_indicators.txt."
    },
    {
      "claimId": "SYM-5",
      "claimText": "Tension",
      "sourceAgent": "symptom",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-003",
        "ANX-004"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.701, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_indicators.txt."
    },
    {
      "claimId": "SYM-6",
      "claimText": "Functional impairment",
      "sourceAgent": "symptom",
      "supportStatus": "partially_supported",
      "citedChunkIds": [
        "ANX-007",
        "ANX-004"
      ],
      "validationNote": "Claim has partial knowledge-base support (cosine similarity: 0.615, threshold: 0.55–0.72). Treat with caution; evidence from: anxiety_indicators.txt, anxiety_indicators.txt."
    }
  ],
  "differentiationAssessment": {
    "primaryLean": "unclear",
    "supportingChunkIds": [],
    "reasoning": "Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category."
  },
  "overallConsistencyNotes": "Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 10 claims evaluated: 3 supported, 7 partially supported, 0 unsupported.",
  "riskLevel": "moderate"
}
```

## Final Report
```md
# AnxioSense Screening Support Report

## 0. GAD-7 Self-Report Screening

GAD-7 Self-Report Screening
Concern Pattern: Elevated Concern Pattern

Your responses over the past two weeks:
  1. Feeling nervous, anxious, or on edge
     → More than half the days
  2. Not being able to stop or control worrying
     → More than half the days
  3. Worrying too much about different things
     → More than half the days
  4. Trouble relaxing
     → Several days
  5. Being so restless that it is hard to sit still
     → More than half the days
  6. Becoming easily annoyed or irritable
     → More than half the days
  7. Feeling afraid, as if something awful might happen
     → Nearly every day

Your responses suggest several experiences that are commonly associated with anxiety and may be affecting your well-being. It may be beneficial to discuss these concerns with a healthcare professional who can provide a more comprehensive assessment and appropriate guidance.

Note: The GAD-7 is a validated self-report screening instrument used 
as an internal reference. It is not a diagnostic tool. This result 
should not be considered a clinical assessment. If you have concerns 
about your mental health, please speak with a qualified healthcare professional.

# AnxioSense Screening Support Report

## 1. Input Mode
This report was generated from journal / self-report entries.

## 2. Summary of Concern
The available text suggests that the individual may be experiencing emotions such as anxiety, stress, frustration, and fear. It also appears to be consistent with some indicators related to anxiety, including excessive worry, sleep disruption, concentration difficulty, restlessness, tension, and functional impairment.

## 3. Emotional Indicators
- Anxiety (partial evidence)
- Stress (partial evidence)
- Frustration (partial evidence)
- Fear (partial evidence)

## 4. Anxiety-Related Indicators
- Excessive worry (strong evidence)
- Sleep disruption (strong evidence)
- Concentration difficulty (strong evidence)
- Restlessness (partial evidence)
- Tension (partial evidence)
- Functional impairment (partial evidence)

## 5. Supporting Evidence
The following excerpts from the clinical knowledge base supported the validated findings:
1. "Reduced ability to focus or make decisions, present in both anxiety and depressive presentations..." (CHUNK_ID: SHARED-002)
2. "Marked symptoms of anxiety persisting for at least several months..." (ICD-11 6B00, WHO (2025-01))
3. "Disruption to normal sleep, present in both anxiety and depressive presentations..." (CHUNK_ID: SHARED-001)
4. "Autonomic/physical arousal: racing heart, sweating, trembling, gastrointestinal problems..." (CHUNK_ID: DIFF-001)

## 6. Contextual Factors
No contextual factors were identified in the available information.

## 7. Referral and Safety Recommendation
Based on the validated findings, a low referral level is suggested. However, it is essential to remember that this report should not be used as a replacement for professional advice or a comprehensive clinical assessment.

## 8. Limitations
This report is based only on the information provided in the journal entries and may have been affected by missing context. The findings do not constitute a clinical diagnosis, and if these experiences persist, worsen, or significantly affect daily life, it is advisable to seek advice from a qualified healthcare professional for a comprehensive assessment. This report is intended for screening support only.

---

## Clinician Details *(restricted — do not share with patient)*

**GAD-7 Raw Score:** 14/21
**Clinical Severity:** Moderate anxiety (10–14)

**Per-Item Breakdown:**
  1. Feeling nervous, anxious, or on edge
     → More than half the days (2)
  2. Not being able to stop or control worrying
     → More than half the days (2)
  3. Worrying too much about different things
     → More than half the days (2)
  4. Trouble relaxing
     → Several days (1)
  5. Being so restless that it is hard to sit still
     → More than half the days (2)
  6. Becoming easily annoyed or irritable
     → More than half the days (2)
  7. Feeling afraid, as if something awful might happen
     → Nearly every day (3)

**Differentiation Assessment:** unclear
**Differentiation Reasoning:** Differentiation evidence did not meet the similarity threshold. Presentation cannot be confidently assigned to a single category.
**Validation Notes:** Validation uses cosine similarity thresholds (supported ≥ 0.72, partially_supported ≥ 0.55, unsupported < 0.55). 10 claims evaluated: 3 supported, 7 partially supported, 0 unsupported.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*
```
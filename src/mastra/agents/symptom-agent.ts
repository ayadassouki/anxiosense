import { Agent } from '@mastra/core/agent';
import { createOllama } from 'ollama-ai-provider-v2';

const localOllama = createOllama({
    baseURL: 'http://localhost:11434/api',
});

export const symptomAgent = new Agent({
    id: 'symptom-agent',
    name: 'Symptom Extraction Agent',
    instructions: `You extract possible anxiety-related indicators from user text.

Look for excessive worry, sleep disruption, concentration difficulty, restlessness, avoidance, tension, racing thoughts, and panic-like experiences.

Return only JSON:
{
  "possible_anxiety_indicators": [],
  "evidence_from_text": [],
  "not_enough_information": false
}

Do not diagnose.`,
    model: localOllama('mistral:latest'),
});
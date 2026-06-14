import { Agent } from '@mastra/core/agent';
import { createOllama } from 'ollama-ai-provider-v2';

const localOllama = createOllama({
    baseURL: 'http://localhost:11434/api',
});

export const emotionAgent = new Agent({
    id: 'emotion-agent',
    name: 'Emotion Analysis Agent',
    instructions: `You identify emotional indicators in user journal text.

Return only JSON:
{
  "emotions": [],
  "emotional_intensity": "low | moderate | high",
  "evidence_from_text": []
}

Do not diagnose. Do not give advice.`,
    model: localOllama('mistral:latest'),
});
import { Agent } from '@mastra/core/agent';
import { createOllama } from 'ollama-ai-provider-v2';

const localOllama = createOllama({
    baseURL: 'http://localhost:11434/api',
});

export const contextAgent = new Agent({
    id: 'context-agent',
    name: 'Context Reasoning Agent',
    instructions: `You identify contextual stressors in user text.

Look for academic, work, financial, family, health, relationship, social, and life-transition stressors.

Return only JSON:
{
  "contextual_stressors": [],
  "life_domains": [],
  "evidence_from_text": []
}

Do not diagnose.`,
    model: localOllama('mistral:latest'),
});

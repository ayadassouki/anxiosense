
import { Mastra } from '@mastra/core/mastra';
import { PinoLogger } from '@mastra/loggers';
import { LibSQLStore } from '@mastra/libsql';
import { DuckDBStore } from "@mastra/duckdb";
import { MastraCompositeStore } from '@mastra/core/storage';
import { Observability, MastraStorageExporter, SensitiveDataFilter } from '@mastra/observability';
import { emotionAnalysisAgent } from './agents/emotion-analysis-agent';
import { anxietySymptomExtractionAgent } from './agents/anxiety-symptom-extraction-agent';
import { contextualStressorAnalysisAgent } from './agents/contextual-stressor-analysis-agent';
import { referralSafetyAssessmentAgent } from './agents/referral-safety-assessment-agent';
import { anxietyScreeningAssessmentWorkflow } from './workflows/anxiety-screening-assessment-workflow';
import { screeningReportGenerationAgent } from './agents/screening-report-generation-agent';
import { crossAgentOutputValidationAgent } from './agents/cross-agent-output-validation-agent';

// Hosted-demo switch. Tracing (DuckDB observability store) is ON unless
// ANXIOSENSE_DISABLE_TRACING=true. Unset = identical to the experiment setup.
// The hosted demo disables it: the DuckDB store grew memory while idle on Railway.
// Tracing is passive; agents, workflow, RAG, /run and /evaluate are unaffected.
const tracingEnabled = process.env.ANXIOSENSE_DISABLE_TRACING !== 'true';

export const mastra = new Mastra({
  workflows: { anxiosenseWorkflow: anxietyScreeningAssessmentWorkflow },
  agents: {
    emotionAgent: emotionAnalysisAgent,
    symptomAgent: anxietySymptomExtractionAgent,
    contextAgent: contextualStressorAnalysisAgent,
    referralAgent: referralSafetyAssessmentAgent,
    validationAgent: crossAgentOutputValidationAgent,
    reportAgent: screeningReportGenerationAgent,
  },
  storage: new MastraCompositeStore({
    id: 'composite-storage',
    default: new LibSQLStore({
      id: "mastra-storage",
      url: "file:./mastra.db",
    }),
    ...(tracingEnabled
      ? { domains: { observability: await new DuckDBStore().getStore('observability') } }
      : {}),
  }),
  logger: new PinoLogger({
    name: 'Mastra',
    level: 'info',
  }),
  ...(tracingEnabled
    ? {
        observability: new Observability({
          configs: {
            default: {
              serviceName: 'mastra',
              exporters: [
                new MastraStorageExporter(), // Persists observability events to local DuckDB storage only
              ],
              spanOutputProcessors: [
                new SensitiveDataFilter(), // Redacts sensitive data like passwords, tokens, keys
              ],
            },
          },
        }),
      }
    : {}),
});

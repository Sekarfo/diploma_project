import type { AppSettings, FeedbackRecord, Vacancy } from "../types";
import {
  createVacancy,
  getAnalyticsSummary,
  getDashboardSummary,
  listShortlistCandidates,
  listVacancies,
  signoutUser,
} from "./realServer";
import {
  generateShortlist,
  getCandidateProfile,
  getProcessingJob,
  getSettings,
  getVacancy,
  listCandidates,
  listFeedbackRecords,
  listIntegrations,
  sendFeedbackToRetraining,
  updateFeedbackRecord,
  updateSettings,
  updateShortlistDecision,
  updateVacancy,
} from "./mockServer";

export const api = {
  auth: {
    signout: signoutUser,
  },
  vacancies: {
    list: listVacancies,
    get: getVacancy,
    create: createVacancy,
    update: (
      vacancyId: string,
      updates: {
        extractedSkills?: string[];
        weights?: Vacancy["weights"];
      }
    ) => updateVacancy(vacancyId, updates),
    generateShortlist,
  },
  processing: {
    get: getProcessingJob,
  },
  dashboard: {
    summary: getDashboardSummary,
  },
  shortlists: {
    list: listShortlistCandidates,
    setDecision: updateShortlistDecision,
  },
  candidates: {
    list: listCandidates,
    getProfile: getCandidateProfile,
  },
  feedback: {
    list: listFeedbackRecords,
    update: (
      recordId: string,
      payload: Pick<FeedbackRecord, "decision" | "reason">
    ) => updateFeedbackRecord(recordId, payload),
    sendToRetraining: sendFeedbackToRetraining,
  },
  analytics: {
    summary: getAnalyticsSummary,
  },
  integrations: {
    list: listIntegrations,
  },
  settings: {
    get: getSettings,
    update: (patch: Partial<AppSettings>) => updateSettings(patch),
  },
};

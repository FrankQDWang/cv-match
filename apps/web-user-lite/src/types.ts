export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

export type AgentShortlistCandidate = {
  candidateId: string;
  externalIdentityId: string;
  name: string;
  title: string;
  company: string;
  location: string;
  summary: string;
  reason: string;
  score: number;
  sourceRound: number;
};

export type ResumeWorkExperienceItem = {
  company: string;
  title: string;
  duration: string | null;
  startTime: string | null;
  endTime: string | null;
  summary: string | null;
};

export type ResumeEducationItem = {
  school: string;
  degree: string;
  major: string;
  startTime: string | null;
  endTime: string | null;
};

export type ResumeProjection = {
  workYear: number | null;
  currentLocation: string | null;
  expectedLocation: string | null;
  jobState: string | null;
  expectedSalary: string | null;
  age: number | null;
  education: ResumeEducationItem[];
  workExperience: ResumeWorkExperienceItem[];
  workSummaries: string[];
  projectNames: string[];
};

export type CandidateDetailResponse = {
  candidate: {
    candidateId: string;
    externalIdentityId: string;
    name: string;
    title: string;
    company: string;
    location: string;
    summary: string;
  };
  resumeView: {
    snapshotId: string;
    projection: ResumeProjection;
  };
  aiAnalysis: {
    status: string;
    summary: string;
    evidenceSpans: string[];
    riskFlags: string[];
  };
  verdictHistory: Array<{
    verdict: string;
    reasons: string[];
    notes: string | null;
    actorId: string;
    createdAt: string;
  }>;
};

export type RunResponse = {
  runId: string;
  status: RunStatus;
  errorMessage: string | null;
  finalShortlist: AgentShortlistCandidate[];
};

export type CreateRunResponse = {
  runId: string;
  status: 'queued' | 'running';
};

export type DetailLoadState =
  | { status: 'idle'; detail: null; error: string }
  | { status: 'loading'; detail: null; error: string }
  | { status: 'loaded'; detail: CandidateDetailResponse; error: string }
  | { status: 'error'; detail: null; error: string };

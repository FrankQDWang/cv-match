import type { components } from '../api/schema';

export type BootstrapAdminInput = components['schemas']['WorkbenchBootstrapRequest'];
export type BootstrapResponse = components['schemas']['WorkbenchBootstrapResponse'];
export type LoginInput = components['schemas']['WorkbenchLoginRequest'];
export type MeResponse = components['schemas']['WorkbenchMeResponse'];
export type WorkbenchUser = components['schemas']['WorkbenchUserResponse'];
export type WorkbenchWorkspace = components['schemas']['WorkbenchWorkspaceResponse'];
export type WorkbenchSession = components['schemas']['WorkbenchSessionResponse'];
export type WorkbenchSessionListResponse = components['schemas']['WorkbenchSessionListResponse'];
export type WorkbenchCandidateReviewItem =
	components['schemas']['WorkbenchCandidateReviewItemResponse'];
export type WorkbenchCandidateReviewQueueResponse =
	components['schemas']['WorkbenchCandidateReviewQueueResponse'];
export type WorkbenchEvent = components['schemas']['WorkbenchEventResponse'];
export type WorkbenchEventListResponse = components['schemas']['WorkbenchEventListResponse'];
export type WorkbenchGraphCandidateListResponse =
	components['schemas']['WorkbenchGraphCandidateListResponse'];
export type WorkbenchGraphCandidateSummary =
	components['schemas']['WorkbenchGraphCandidateSummaryResponse'];
export type WorkbenchGraphCandidateResumeSnapshot =
	components['schemas']['WorkbenchGraphCandidateResumeSnapshotResponse'];

from seektalent.models import ResumeCandidate
from seektalent.providers.cts.mapper import build_provider_candidate


def test_cts_candidate_mapper_builds_resume_candidate() -> None:
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="source-1",
        snapshot_sha256="snap",
        dedup_key="resume-1",
        search_text="python engineer",
        raw={"resumeId": "resume-1"},
    )

    mapped = build_provider_candidate(candidate)

    assert mapped.resume_id == "resume-1"
    assert mapped.dedup_key == "resume-1"


def test_cts_candidate_mapper_isolates_mutable_fields() -> None:
    candidate = ResumeCandidate(
        resume_id="resume-1",
        source_resume_id="source-1",
        snapshot_sha256="snap",
        dedup_key="resume-1",
        education_summaries=["BS Computer Science"],
        work_experience_summaries=["Built matching systems"],
        search_text="python engineer",
        raw={"resumeId": "resume-1", "tags": ["python"]},
    )

    mapped = build_provider_candidate(candidate)
    mapped.raw["resumeId"] = "resume-2"
    mapped.raw["tags"].append("ml")
    mapped.education_summaries.append("MS AI")
    mapped.work_experience_summaries.append("Led search infra")

    assert candidate.raw == {"resumeId": "resume-1", "tags": ["python"]}
    assert candidate.education_summaries == ["BS Computer Science"]
    assert candidate.work_experience_summaries == ["Built matching systems"]

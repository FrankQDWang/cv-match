from __future__ import annotations

import argparse
from pathlib import Path

from seektalent.replay_tuning import run_replay_tuning
from seektalent.resources import repo_root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-set", default="v1")
    parser.add_argument("--case-set", choices=["canonical", "tuning", "all"], default="all")
    parser.add_argument(
        "--output-dir",
        default=str(repo_root() / "artifacts" / "runtime" / "evals" / "replay-tuning"),
    )
    args = parser.parse_args()
    run_replay_tuning(
        repo_root=repo_root(),
        output_dir=Path(args.output_dir),
        profile_set=args.profile_set,
        case_set=args.case_set,
    )


if __name__ == "__main__":
    main()

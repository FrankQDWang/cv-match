import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "apps" / "liepin-worker"


def test_liepin_worker_boundary_checker_rejects_forbidden_snippets(tmp_path):
    forbidden = tmp_path / "forbidden.ts"
    forbidden.write_text(
        """
        import { request, type APIRequestContext } from "playwright";
        import { OpenCLI } from "@opencli/sdk";

        export async function run(page: any, context: any, playwright: any) {
          const typed: APIRequestContext | null = null;
          await page.request.get("https://example.test");
          await context["request"].post("https://example.test");
          await playwright.request.newContext();
          await request.newContext();
          return typed;
        }
        """,
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bun", "scripts/checkBoundaries.ts", str(forbidden)],
        cwd=WORKER,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "APIRequestContext" in output
    assert "page.request" in output or 'context["request"]' in output
    assert "request.newContext" in output
    assert "OpenCLI" in output

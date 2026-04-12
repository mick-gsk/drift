from __future__ import annotations

from pathlib import Path

from drift.config import DriftConfig
from drift.ingestion.test_detection import classify_file_context, is_test_file
from drift.models import ParseResult
from drift.signals.cognitive_complexity import CognitiveComplexitySignal


def test_issue_311_qa_lab_mock_server_anonymous_handler_is_test_context(
  tmp_path: Path,
) -> None:
    file_path = Path("extensions/qa-lab/src/mock-openai-server.ts")
    assert is_test_file(file_path)
    assert classify_file_context(file_path) == "test"

    # Uses an anonymous request-handler callback with intentionally complex branching.
    source = """
import { createServer } from "node:http";

export function startQaMockOpenAiServer(): void {
  const server = createServer(async (req, res) => {
    const path = req.url ?? "/";
    if (path === "/v1/chat/completions") {
      if (req.method === "POST") {
        if (Math.random() > 0.5) {
          res.statusCode = 200;
        } else {
          res.statusCode = 202;
        }
      } else {
        res.statusCode = 405;
      }
    } else if (path === "/v1/responses") {
      if (req.method === "POST") {
        if (Math.random() > 0.5) {
          res.statusCode = 200;
        } else {
          res.statusCode = 500;
        }
      } else {
        res.statusCode = 405;
      }
    } else {
      if (req.method === "GET") {
        if (Math.random() > 0.5) {
          res.statusCode = 404;
        } else {
          res.statusCode = 410;
        }
      } else {
        res.statusCode = 400;
      }
    }
    res.end();
  });
  server.listen(0);
}
""".strip()

    tmp_root = tmp_path
    target = tmp_root / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")

    parse_result = ParseResult(
        file_path=file_path,
        language="typescript",
        functions=[],
    )

    signal = CognitiveComplexitySignal()
    signal._repo_path = tmp_root
    findings = signal.analyze([parse_result], {}, DriftConfig())

    assert findings == []

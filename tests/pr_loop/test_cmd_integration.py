"""CLI integration tests for drift pr-loop (T039)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from drift.pr_loop._cmd import pr_loop_cmd
from drift.pr_loop._models import LoopExitStatus, LoopState


def _make_state(status: LoopExitStatus = LoopExitStatus.APPROVED) -> LoopState:
    return LoopState(pr_number=42, round=2, status=status)


class TestPrLoopExitCodes:
    def _run(
        self,
        args: list[str],
        state: LoopState | None = None,
        gh_auth_ok: bool = True,
    ) -> object:
        runner = CliRunner()
        mock_state = state or _make_state(LoopExitStatus.APPROVED)

        with (
            patch("drift.pr_loop._cmd.subprocess.run") as mock_subprocess,
            patch("drift.pr_loop._cmd.DriftConfig.load") as mock_load,
            patch("drift.pr_loop._cmd.loop_until_approved", return_value=mock_state),
        ):
            if not gh_auth_ok:
                mock_subprocess.side_effect = Exception("auth failed")
            else:
                mock_subprocess.return_value = MagicMock(returncode=0)

            from drift.config._loader import DriftConfig, PrLoopConfig

            cfg = DriftConfig(pr_loop=PrLoopConfig(reviewers=["github-copilot[bot]"]))
            mock_load.return_value = cfg
            result = runner.invoke(pr_loop_cmd, args, catch_exceptions=False)
        return result

    def test_exit_code_0_on_approved(self) -> None:
        result = self._run(["42"], _make_state(LoopExitStatus.APPROVED))
        assert result.exit_code == 0

    def test_exit_code_1_on_escalated(self) -> None:
        result = self._run(["42"], _make_state(LoopExitStatus.ESCALATED))
        assert result.exit_code == 1

    def test_exit_code_3_on_gh_auth_failure(self) -> None:
        runner = CliRunner()
        import subprocess as _sp

        with patch(
            "drift.pr_loop._cmd.subprocess.run", side_effect=_sp.CalledProcessError(1, "gh")
        ):
            result = runner.invoke(pr_loop_cmd, ["42"])
        assert result.exit_code == 3

    def test_exit_zero_flag_always_exits_0(self) -> None:
        result = self._run(["42", "--exit-zero"], _make_state(LoopExitStatus.ESCALATED))
        assert result.exit_code == 0

    def test_exit_zero_flag_with_error_state(self) -> None:
        result = self._run(["42", "--exit-zero"], _make_state(LoopExitStatus.ERROR))
        assert result.exit_code == 0


class TestPrLoopDryRun:
    def test_dry_run_passes_flag_to_loop(self) -> None:
        runner = CliRunner()
        with (
            patch("drift.pr_loop._cmd.subprocess.run") as mock_subprocess,
            patch("drift.pr_loop._cmd.DriftConfig.load") as mock_load,
            patch("drift.pr_loop._cmd.loop_until_approved") as mock_loop,
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)
            from drift.config._loader import DriftConfig, PrLoopConfig

            cfg = DriftConfig(pr_loop=PrLoopConfig(reviewers=["alice"]))
            mock_load.return_value = cfg
            mock_loop.return_value = _make_state(LoopExitStatus.APPROVED)

            runner.invoke(pr_loop_cmd, ["42", "--dry-run"], catch_exceptions=False)

            call_kwargs = mock_loop.call_args
            assert (
                call_kwargs.kwargs.get("dry_run") is True or call_kwargs[1].get("dry_run") is True
            )


class TestPrLoopJsonOutput:
    def test_json_output_matches_schema(self) -> None:
        runner = CliRunner()
        with (
            patch("drift.pr_loop._cmd.subprocess.run") as mock_subprocess,
            patch("drift.pr_loop._cmd.DriftConfig.load") as mock_load,
            patch("drift.pr_loop._cmd.loop_until_approved") as mock_loop,
        ):
            mock_subprocess.return_value = MagicMock(returncode=0)
            from drift.config._loader import DriftConfig, PrLoopConfig

            cfg = DriftConfig(pr_loop=PrLoopConfig(reviewers=["github-copilot[bot]"]))
            mock_load.return_value = cfg
            mock_loop.return_value = _make_state(LoopExitStatus.APPROVED)

            result = runner.invoke(pr_loop_cmd, ["42", "--format", "json"], catch_exceptions=False)

        output = json.loads(result.output)
        assert "pr_number" in output
        assert "status" in output
        assert "rounds_completed" in output
        assert "reviewers" in output
        assert "verdicts" in output
        assert "escalated" in output
        assert "exit_code" in output

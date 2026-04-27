"""Tests for Pattern Fragmentation signal."""

from pathlib import Path

from drift.config import DeferredArea, DriftConfig
from drift.models import (
    Finding,
    ParseResult,
    PatternCategory,
    PatternInstance,
    Severity,
    SignalType,
)
from drift.signals.pattern_fragmentation import PatternFragmentationSignal


def _make_pattern(
    category: PatternCategory,
    module: str,
    func: str,
    fingerprint: dict,
    line: int = 1,
) -> PatternInstance:
    return PatternInstance(
        category=category,
        file_path=Path(f"{module}/{func}.py"),
        function_name=func,
        start_line=line,
        end_line=line + 5,
        fingerprint=fingerprint,
    )


def _wrap(patterns: list[PatternInstance]) -> list[ParseResult]:
    """Wrap PatternInstances into a minimal ParseResult list."""
    return [
        ParseResult(
            file_path=Path("dummy.py"),
            language="python",
            patterns=patterns,
        )
    ]


def test_no_patterns_returns_no_findings():
    signal = PatternFragmentationSignal()
    findings = signal.analyze(_wrap([]), {}, None)
    assert findings == []


def test_single_variant_no_fragmentation():
    # All patterns in one module use the same fingerprint → no fragmentation
    patterns = [
        _make_pattern(
            PatternCategory.ERROR_HANDLING,
            "services",
            f"func_{i}",
            {
                "handler_count": 1,
                "handlers": [{"exception_type": "ValueError", "actions": ["raise"]}],
            },
        )
        for i in range(4)
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert findings == []


def test_two_variants_detected():
    # Two distinct non-propagation action strategies → fragmentation
    fp_a = {
        "handler_count": 1,
        "handlers": [{"exception_type": "ValueError", "actions": ["log", "return"]}],
    }
    fp_b = {
        "handler_count": 1,
        "handlers": [{"exception_type": "Exception", "actions": ["print"]}],
    }

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "services", "func_a", fp_a),
        _make_pattern(PatternCategory.ERROR_HANDLING, "services", "func_b", fp_a),
        _make_pattern(PatternCategory.ERROR_HANDLING, "services", "func_c", fp_b),
    ]

    signal = PatternFragmentationSignal()
    findings = signal.analyze(_wrap(patterns), {}, None)

    assert len(findings) == 1
    f = findings[0]
    assert f.signal_type == SignalType.PATTERN_FRAGMENTATION
    assert f.metadata["num_variants"] == 2
    assert f.metadata["total_instances"] == 3
    assert f.metadata["canonical_count"] == 2  # fp_a used twice
    assert 0.4 <= f.score <= 0.6  # 1 - 1/2 = 0.5
    assert f.fix is not None
    assert "Consolidate to the dominant pattern" in f.fix
    assert "exemplar:" in f.fix
    assert "Deviations:" in f.fix
    assert ".py:" in f.fix
    assert "Konsolidiere" not in f.fix


def test_error_handling_propagation_excluded_from_fragmentation():
    # Issue #526: try/except: raise (pure propagation, no logging) must not count
    # as a variant alongside sentinel-return patterns.
    # Only the 2 sentinel patterns remain after filtering → 1 variant → no finding.
    fp_raise = {
        "handler_count": 1,
        "handlers": [{"exception_type": "OSError", "actions": ["raise"]}],
    }
    fp_return = {
        "handler_count": 1,
        "handlers": [{"exception_type": "ValueError", "actions": ["return"]}],
    }

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "atomic_write", fp_raise),
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "load_status", fp_return),
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "load_history", fp_return),
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert findings == [], "Propagation-only raise must not fragment with sentinel-return patterns"


def test_error_handling_log_and_rethrow_is_not_propagation():
    # log-and-rethrow (["log", "raise"]) IS a deliberate style and must remain
    # in the fragmentation analysis (contrast with pure raise = propagation).
    fp_log_raise = {
        "handler_count": 1,
        "handlers": [{"exception_type": "Exception", "actions": ["log", "raise"]}],
    }
    fp_return = {
        "handler_count": 1,
        "handlers": [{"exception_type": "Exception", "actions": ["return"]}],
    }

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "workers", "task_a", fp_log_raise),
        _make_pattern(PatternCategory.ERROR_HANDLING, "workers", "task_b", fp_log_raise),
        _make_pattern(PatternCategory.ERROR_HANDLING, "workers", "task_c", fp_return),
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1, "log-and-rethrow vs sentinel-return IS fragmentation"


def test_error_handling_propagation_excluded_metadata():
    # When propagation patterns are filtered, metadata should reflect the count.
    # ["other", "raise"] (cleanup + rethrow) is also propagation (no log before raise).
    fp_cleanup_raise = {
        "handler_count": 1,
        "handlers": [{"exception_type": "OSError", "actions": ["other", "raise"]}],
    }
    fp_log_return = {
        "handler_count": 1,
        "handlers": [{"exception_type": "ValueError", "actions": ["log", "return"]}],
    }
    fp_sentinel = {
        "handler_count": 1,
        "handlers": [{"exception_type": "Exception", "actions": ["return"]}],
    }

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "core", "io_write", fp_cleanup_raise),
        _make_pattern(PatternCategory.ERROR_HANDLING, "core", "load_a", fp_log_return),
        _make_pattern(PatternCategory.ERROR_HANDLING, "core", "load_b", fp_log_return),
        _make_pattern(PatternCategory.ERROR_HANDLING, "core", "load_c", fp_sentinel),
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    f = findings[0]
    assert f.metadata["propagation_excluded_count"] == 1
    # 2 action variants remain (log+return vs return)
    assert f.metadata["num_variants"] == 2


def test_error_handling_exception_type_not_a_variant():
    # Issue #526: same action strategy with different exception types is NOT fragmentation.
    # return None after ValueError, OSError, JSONDecodeError → all same pattern.
    fp_val = {
        "handler_count": 1,
        "handlers": [{"exception_type": "ValueError", "actions": ["return"]}],
    }
    fp_os = {
        "handler_count": 1,
        "handlers": [{"exception_type": "OSError", "actions": ["return"]}],
    }
    fp_json = {
        "handler_count": 1,
        "handlers": [{"exception_type": "json.JSONDecodeError", "actions": ["return"]}],
    }

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "f1", fp_val),
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "f2", fp_os),
        _make_pattern(PatternCategory.ERROR_HANDLING, "calibration", "f3", fp_json),
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert findings == [], (
        "Same action strategy (return) with different exception types must not be fragmentation"
    )


def test_error_handling_loop_skip_is_captured():
    # continue in except body is now captured as loop_skip (not "other"),
    # verifying the fingerprint improvement in ast_parser._fingerprint_try_block.
    import ast
    import textwrap

    from drift.ingestion.ast_parser import _fingerprint_try_block

    src = textwrap.dedent("""\
        for item in items:
            try:
                process(item)
            except ValueError:
                continue
    """)
    tree = ast.parse(src)
    try_node = next(
        node for node in ast.walk(tree) if isinstance(node, ast.Try)
    )
    fp = _fingerprint_try_block(try_node)
    assert fp["handlers"][0]["actions"] == ["loop_skip"], (
        "continue in except body must map to loop_skip action"
    )


def test_three_variants_higher_score():
    fps = [
        {"h": [{"type": "ValueError", "act": ["raise"]}]},
        {"h": [{"type": "Exception", "act": ["print"]}]},
        {"h": [{"type": "OSError", "act": ["log"]}]},
    ]
    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "core", f"f{i}", fp)
        for i, fp in enumerate(fps)
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    # 1 - 1/3 ≈ 0.667
    assert findings[0].score > 0.6


def test_separate_modules_separate_findings():
    fp_a = {"x": 1}
    fp_b = {"x": 2}

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "mod_a", "f1", fp_a),
        _make_pattern(PatternCategory.ERROR_HANDLING, "mod_a", "f2", fp_b),
        _make_pattern(PatternCategory.ERROR_HANDLING, "mod_b", "f3", fp_a),
        _make_pattern(PatternCategory.ERROR_HANDLING, "mod_b", "f4", fp_b),
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    # Two modules × 1 category = 2 findings
    assert len(findings) == 2


def test_framework_surface_error_handling_is_dampened():
    fps = [
        {"handler": "value_error"},
        {"handler": "exception"},
        {"handler": "os_error"},
        {"handler": "type_error"},
        {"handler": "runtime_error"},
    ]
    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "backend/api/routers", f"f{i}", fp)
        for i, fp in enumerate(fps)
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.score < 0.7
    assert finding.severity == Severity.MEDIUM
    assert finding.metadata["framework_context_dampened"] is True
    assert finding.metadata["framework_context_hints"]


def test_core_error_handling_is_not_dampened():
    fps = [
        {"handler": "value_error"},
        {"handler": "exception"},
        {"handler": "os_error"},
        {"handler": "type_error"},
        {"handler": "runtime_error"},
    ]
    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "core/domain", f"f{i}", fp)
        for i, fp in enumerate(fps)
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.score >= 0.7
    assert finding.severity == Severity.HIGH
    assert finding.metadata["framework_context_dampened"] is False
    assert finding.metadata["framework_context_hints"] == []


def test_identical_decorator_patterns_no_finding():
    # 5 FastAPI-style routes with identical fingerprints (same structure, different
    # paths/methods) must produce no PFS finding — structural similarity here comes
    # from the framework pattern, not from fragmented logic.
    fp = {
        "has_error_handling": False,
        "has_auth": False,
        "auth_mechanism": None,
        "return_patterns": ["jsonify"],
    }
    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "routes", f"route_{i}", fp) for i in range(5)
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert findings == [], "Identical decorator patterns must not produce any PFS finding"


def test_plugin_architecture_api_fragmentation_is_dampened_to_info():
    # Plugin/extension layouts intentionally vary across plugin boundaries.
    # High-severity PFS should be dampened for extension-specific API surfaces.
    target_fingerprints = [
        {"route": "send-message"},
        {"route": "send-media"},
        {"route": "edit-message"},
        {"route": "delete-message"},
        {"route": "pin-message"},
    ]
    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "extensions/bluebubbles/src", f"f{i}", fp)
        for i, fp in enumerate(target_fingerprints)
    ]
    patterns.extend(
        [
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/discord/src",
                "discord_route",
                {"route": "send-message"},
            ),
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/whatsapp/src",
                "whatsapp_route",
                {"route": "send-message"},
            ),
        ]
    )

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.file_path.as_posix() == "extensions/bluebubbles/src"
    assert finding.severity == Severity.INFO
    assert finding.metadata["plugin_context_dampened"] is True
    assert finding.metadata["plugin_context_hints"]
    assert finding.metadata["plugin_boundary_variation_expected"] is True


def test_combined_framework_and_plugin_dampening_caps_to_info():
    # Error-handling variants inside one extension API surface can be expected
    # when several plugins expose distinct external-provider contracts.
    error_fingerprints = [
        {"handler": "value_error"},
        {"handler": "exception"},
        {"handler": "os_error"},
        {"handler": "type_error"},
        {"handler": "runtime_error"},
    ]
    patterns = [
        _make_pattern(
            PatternCategory.ERROR_HANDLING,
            "extensions/anthropic/src/api",
            f"err_{i}",
            fp,
        )
        for i, fp in enumerate(error_fingerprints)
    ]
    patterns.extend(
        [
            _make_pattern(
                PatternCategory.ERROR_HANDLING,
                "extensions/openai/src/api",
                "openai_err",
                {"handler": "provider_specific"},
            ),
            _make_pattern(
                PatternCategory.ERROR_HANDLING,
                "extensions/sglang/src/api",
                "sglang_err",
                {"handler": "provider_specific"},
            ),
        ]
    )
    patterns.extend(
        [
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/anthropic/src/api",
                "route_a",
                {"route": "messages"},
            ),
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/openai/src/api",
                "route_b",
                {"route": "chat"},
            ),
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/sglang/src/api",
                "route_c",
                {"route": "generate"},
            ),
        ]
    )

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    target = [
        f
        for f in findings
        if f.file_path.as_posix() == "extensions/anthropic/src/api"
        and f.metadata.get("category") == PatternCategory.ERROR_HANDLING.value
    ]

    assert len(target) == 1
    finding = target[0]
    assert finding.metadata["framework_context_dampened"] is True
    assert finding.metadata["plugin_context_dampened"] is True
    assert finding.metadata["combined_plugin_framework_cap"] is True
    assert finding.severity == Severity.INFO


def test_issue_266_api_endpoint_variants_in_multi_extension_layout_are_info():
    # In extension monorepos, endpoint heterogeneity across plugin boundaries is
    # expected and should stay informational, not actionable drift urgency.
    browser_fingerprints = [
        {"route": "health"},
        {"route": "messages"},
        {"route": "assets"},
        {"route": "config"},
    ]
    patterns = [
        _make_pattern(
            PatternCategory.API_ENDPOINT,
            "extensions/browser/src/browser/routes",
            f"browser_route_{i}",
            fp,
        )
        for i, fp in enumerate(browser_fingerprints)
    ]
    patterns.extend(
        [
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/discord/src/discord/routes",
                "discord_route",
                {"route": "messages"},
            ),
            _make_pattern(
                PatternCategory.API_ENDPOINT,
                "extensions/matrix/src/matrix/routes",
                "matrix_route",
                {"route": "messages"},
            ),
        ]
    )

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    target = [
        f
        for f in findings
        if f.file_path.as_posix() == "extensions/browser/src/browser/routes"
        and f.metadata.get("category") == PatternCategory.API_ENDPOINT.value
    ]

    assert len(target) == 1
    finding = target[0]
    assert finding.severity == Severity.INFO
    assert finding.metadata["plugin_context_dampened"] is True
    assert finding.metadata["plugin_boundary_variation_expected"] is True
    assert any(
        hint.startswith("inter-plugin-pattern-variation-expected:")
        for hint in finding.metadata["plugin_context_hints"]
    )


def test_issue_266_error_handling_variants_in_multi_extension_layout_are_info():
    browser_error_variants = [
        {"handler": "value_error"},
        {"handler": "exception"},
        {"handler": "os_error"},
        {"handler": "runtime_error"},
    ]
    patterns = [
        _make_pattern(
            PatternCategory.ERROR_HANDLING,
            "extensions/browser/src/browser/core",
            f"browser_err_{i}",
            fp,
        )
        for i, fp in enumerate(browser_error_variants)
    ]
    patterns.extend(
        [
            _make_pattern(
                PatternCategory.ERROR_HANDLING,
                "extensions/discord/src/discord/core",
                "discord_err",
                {"handler": "value_error"},
            ),
            _make_pattern(
                PatternCategory.ERROR_HANDLING,
                "extensions/matrix/src/matrix/core",
                "matrix_err",
                {"handler": "value_error"},
            ),
        ]
    )

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    target = [
        f
        for f in findings
        if f.file_path.as_posix() == "extensions/browser/src/browser/core"
        and f.metadata.get("category") == PatternCategory.ERROR_HANDLING.value
    ]

    assert len(target) == 1
    finding = target[0]
    assert finding.severity == Severity.INFO
    assert finding.metadata["plugin_context_dampened"] is True
    assert finding.metadata["plugin_boundary_variation_expected"] is True


def test_plugin_variation_cap_is_not_applied_for_non_plugin_layout():
    fps = [
        {"route": "a"},
        {"route": "b"},
        {"route": "c"},
        {"route": "d"},
    ]
    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routes", f"route_{i}", fp)
        for i, fp in enumerate(fps)
    ]

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.file_path.as_posix() == "backend/api/routes"
    assert finding.severity == Severity.HIGH
    assert finding.metadata["plugin_context_dampened"] is False
    assert finding.metadata["plugin_boundary_variation_expected"] is False


def test_score_aggregation():
    findings = [
        Finding(
            signal_type=SignalType.PATTERN_FRAGMENTATION,
            severity=Severity.MEDIUM,
            score=0.5,
            title="a",
            description="",
        ),
        Finding(
            signal_type=SignalType.PATTERN_FRAGMENTATION,
            severity=Severity.MEDIUM,
            score=0.7,
            title="b",
            description="",
        ),
    ]
    avg_score = sum(f.score for f in findings) / len(findings)
    assert avg_score == 0.6


# ---------------------------------------------------------------------------
# RETURN_PATTERN detection through PFS
# ---------------------------------------------------------------------------


def test_return_pattern_two_variants_detected():
    """Two different return-strategy fingerprints in one module → PFS finding."""
    fp_none_raise = {"strategies": ["raise", "return_none"]}
    fp_tuple_value = {"strategies": ["return_tuple", "return_value"]}
    patterns = [
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "get_user", fp_none_raise),
        _make_pattern(
            PatternCategory.RETURN_PATTERN,
            "models",
            "get_user_or_raise",
            fp_tuple_value,
        ),
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    assert findings[0].signal_type == SignalType.PATTERN_FRAGMENTATION
    assert "return_pattern" in findings[0].title
    assert findings[0].metadata["num_variants"] == 2


def test_return_pattern_single_variant_no_finding():
    """All functions share the same return-strategy fingerprint → no finding."""
    fp = {"strategies": ["raise", "return_value"]}
    patterns = [
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "func_a", fp),
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "func_b", fp),
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert findings == []


def test_return_pattern_three_variants():
    """Three distinct return-strategy fingerprints → higher fragmentation score."""
    fp_a = {"strategies": ["raise", "return_value"]}
    fp_b = {"strategies": ["return_none", "return_value"]}
    fp_c = {"strategies": ["return_tuple"]}
    patterns = [
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "get_user", fp_a),
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "get_or_raise", fp_b),
        _make_pattern(PatternCategory.RETURN_PATTERN, "models", "get_result", fp_c),
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    assert findings[0].metadata["num_variants"] == 3
    assert findings[0].score >= 0.5


# ---------------------------------------------------------------------------
# Deferred-file filtering (issue #542)
# ---------------------------------------------------------------------------

def _make_config_with_deferred(*patterns: str) -> DriftConfig:
    return DriftConfig(deferred=[DeferredArea(pattern=p) for p in patterns])


def test_deferred_files_excluded_from_variant_count():
    # Active router: 2 variants → PFS finding
    # Deferred routers: 3 additional variants from deferred files
    # Only active variants should count.
    fp_a = {"route": "variant_a"}
    fp_b = {"route": "variant_b"}
    fp_deferred_c = {"route": "variant_c"}
    fp_deferred_d = {"route": "variant_d"}

    patterns = [
        # Active files: 2 variants → fragmentation
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "admin", fp_a),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "analytics", fp_a),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "auth", fp_b),
        # Deferred files: extra variants that must NOT inflate the count
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "billing", fp_deferred_c),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "marketplace", fp_deferred_d),
    ]

    config = _make_config_with_deferred(
        "backend/api/routers/billing.py",
        "backend/api/routers/marketplace.py",
    )

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, config)
    assert len(findings) == 1, "PFS finding from active variants should remain"
    f = findings[0]
    # Only 2 active variants counted (fp_a + fp_b), not 4
    assert f.metadata["num_variants"] == 2
    assert f.metadata["deferred_excluded_count"] == 2
    # Deferred files must not appear in related_files
    related_posix = {p.as_posix() for p in f.related_files}
    assert "backend/api/routers/billing.py" not in related_posix
    assert "backend/api/routers/marketplace.py" not in related_posix


def test_deferred_only_variants_suppresses_finding():
    # All non-canonical variants come from deferred files → after filtering,
    # only one variant remains (canonical) → no fragmentation finding.
    fp_canonical = {"route": "canonical"}
    fp_deferred = {"route": "deferred_variant"}

    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "admin", fp_canonical),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "analytics", fp_canonical),
        # Deferred file introduces the only second variant
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "billing", fp_deferred),
    ]

    config = _make_config_with_deferred("backend/api/routers/billing.py")

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, config)
    assert findings == [], (
        "No finding when all non-canonical variants are from deferred files"
    )


def test_deferred_excluded_count_zero_when_no_deferred_config():
    # Without deferred config, deferred_excluded_count must be 0 in metadata.
    fp_a = {"x": 1}
    fp_b = {"x": 2}
    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "admin", fp_a),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "auth", fp_b),
    ]
    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, None)
    assert len(findings) == 1
    assert findings[0].metadata["deferred_excluded_count"] == 0


def test_deferred_glob_wildcard_matches_prefix():
    # Pattern like "backend/api/routers/billing*" should match billing.py,
    # billing_v2.py, etc.
    fp_canonical = {"route": "v1"}
    fp_deferred = {"route": "v2"}

    patterns = [
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "admin", fp_canonical),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "analytics", fp_canonical),
        _make_pattern(PatternCategory.API_ENDPOINT, "backend/api/routers", "billing_v2", fp_deferred),
    ]

    config = _make_config_with_deferred("backend/api/routers/billing*")

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, config)
    assert findings == [], "Glob wildcard deferred pattern should match billing_v2.py"


def test_deferred_does_not_affect_unrelated_modules():
    # Deferred pattern for routers/billing* must not suppress findings
    # in an entirely different module (services/).
    fp_a = {"x": 1}
    fp_b = {"x": 2}

    patterns = [
        _make_pattern(PatternCategory.ERROR_HANDLING, "services", "svc_a", fp_a),
        _make_pattern(PatternCategory.ERROR_HANDLING, "services", "svc_b", fp_b),
    ]

    config = _make_config_with_deferred("backend/api/routers/billing*")

    findings = PatternFragmentationSignal().analyze(_wrap(patterns), {}, config)
    assert len(findings) == 1, "Deferred pattern for routers must not suppress services/ finding"

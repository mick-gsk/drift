"""Translator — renders contract results in plain, non-technical language."""

from __future__ import annotations

from drift.intent.models import ContractResult, ContractStatus


def contract_result_to_plain(result: ContractResult) -> str:
    """Render a single contract result as a plain-language line.

    Returns one of:
        ✅ "description_human"
        ❌ "Problem: description_human"
        ⚠️  "Konnte nicht automatisch geprüft werden: description_human"
    """
    desc = result.contract.description_human
    if result.status == ContractStatus.FULFILLED:
        return f"\u2705 {desc}"
    if result.status == ContractStatus.VIOLATED:
        return f"\u274c Problem: {desc}"
    # UNVERIFIABLE
    return f"\u26a0\ufe0f  Konnte nicht automatisch gepr\u00fcft werden: {desc}"


def results_to_markdown(
    results: list[ContractResult],
    *,
    prompt: str = "",
) -> str:
    """Render a full contract report in plain-language Markdown.

    Parameters
    ----------
    results:
        Contract validation results.
    prompt:
        Original user prompt (shown as context header).

    Returns
    -------
    str
        Markdown report with no technical jargon.
    """
    lines: list[str] = ["# Ergebnis der Pr\u00fcfung", ""]
    if prompt:
        lines.append(f"> {prompt}")
        lines.append("")

    fulfilled = [r for r in results if r.status == ContractStatus.FULFILLED]
    violated = [r for r in results if r.status == ContractStatus.VIOLATED]
    unverifiable = [r for r in results if r.status == ContractStatus.UNVERIFIABLE]

    total = len(results)
    ok = len(fulfilled)

    if violated:
        lines.append(
            f"**{ok} von {total}** Anforderungen sind erf\u00fcllt. "
            f"**{len(violated)}** Problem(e) gefunden."
        )
    elif unverifiable:
        lines.append(
            f"**{ok} von {total}** Anforderungen sind erf\u00fcllt. "
            f"**{len(unverifiable)}** konnte(n) nicht automatisch gepr\u00fcft werden."
        )
    else:
        lines.append(f"Alle **{total}** Anforderungen sind erf\u00fcllt. \U0001f389")

    lines.append("")

    for r in results:
        lines.append(f"- {contract_result_to_plain(r)}")

    lines.append("")
    return "\n".join(lines)


def escalation_message(contract: ContractResult, iteration: int) -> str:
    """Generate a plain-language escalation when repair is exhausted.

    Parameters
    ----------
    contract:
        The still-violated contract.
    iteration:
        How many repair iterations were attempted.

    Returns
    -------
    str
        Human-readable escalation text.
    """
    return (
        f"Dieses Problem konnte nicht automatisch behoben werden: "
        f"{contract.contract.description_human}. "
        f"Bitte beschreibe genauer was du m\u00f6chtest. "
        f"({iteration} Reparaturversuche durchgef\u00fchrt)"
    )

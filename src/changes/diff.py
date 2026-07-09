from difflib import unified_diff


def build_text_diff(
    original_text: str,
    proposed_text: str,
) -> str:
    original_lines = original_text.splitlines()
    proposed_lines = proposed_text.splitlines()

    diff_lines = unified_diff(
        original_lines,
        proposed_lines,
        fromfile="original",
        tofile="proposed",
        lineterm="",
    )

    return "\n".join(diff_lines)
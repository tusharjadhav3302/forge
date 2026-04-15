"""Comment classification for Forge Q&A mode."""

import re
from enum import StrEnum


class CommentType(StrEnum):
    """Type of comment detected in Jira comments."""

    QUESTION = "question"
    APPROVAL = "approval"
    FEEDBACK = "feedback"


# Pattern for @forge ask (case insensitive)
_FORGE_ASK_PATTERN = re.compile(r"^\s*@forge\s+ask", re.IGNORECASE)

# Pattern for question mark at start (allowing leading whitespace)
_QUESTION_MARK_PATTERN = re.compile(r"^\s*\?")

# Approval keywords (case insensitive)
_APPROVAL_KEYWORDS = [
    "approved",
    "lgtm",
    "looks good to me",
    "looks good",
]


def classify_comment(comment_text: str) -> CommentType:
    """Classify a Jira comment into question, approval, or feedback.

    Classification rules:
    - Questions: Comments starting with '?' or '@forge ask' (case-insensitive)
    - Approvals: Comments containing approval keywords like 'approved', 'lgtm', etc.
    - Feedback: Everything else (default)

    Args:
        comment_text: The text of the comment to classify.

    Returns:
        The classified comment type.
    """
    # Handle empty or whitespace-only comments
    if not comment_text or not comment_text.strip():
        return CommentType.FEEDBACK

    # Check for question markers first (takes precedence)
    if _QUESTION_MARK_PATTERN.match(comment_text):
        return CommentType.QUESTION

    if _FORGE_ASK_PATTERN.match(comment_text):
        return CommentType.QUESTION

    # Check for approval keywords
    lower_text = comment_text.lower()
    for keyword in _APPROVAL_KEYWORDS:
        if keyword in lower_text:
            return CommentType.APPROVAL

    # Default to feedback
    return CommentType.FEEDBACK

"""Tests for comment classification functionality."""

from forge.workflow.utils import CommentType, classify_comment


class TestClassifyComment:
    """Test cases for the classify_comment function."""

    # Question detection tests
    def test_question_with_question_mark_prefix(self) -> None:
        """Comments starting with ? should be classified as questions."""
        assert classify_comment("?Why REST?") == CommentType.QUESTION

    def test_question_with_question_mark_and_space(self) -> None:
        """Question mark followed by space should be a question."""
        assert classify_comment("? What is the reason for this?") == CommentType.QUESTION

    def test_question_with_forge_ask_prefix(self) -> None:
        """Comments starting with @forge ask should be questions."""
        assert classify_comment("@forge ask explain this") == CommentType.QUESTION

    def test_question_with_forge_ask_case_insensitive(self) -> None:
        """@forge ask should be case insensitive."""
        assert classify_comment("@Forge Ask why") == CommentType.QUESTION
        assert classify_comment("@FORGE ASK details") == CommentType.QUESTION
        assert classify_comment("@Forge ask more info") == CommentType.QUESTION

    def test_question_with_forge_ask_no_trailing_text(self) -> None:
        """@forge ask with minimal content."""
        assert classify_comment("@forge ask") == CommentType.QUESTION

    # Feedback tests (default)
    def test_feedback_as_default(self) -> None:
        """Comments without question markers should be feedback."""
        assert classify_comment("Please add more detail") == CommentType.FEEDBACK
        assert classify_comment("Can you expand on this section") == CommentType.FEEDBACK

    def test_approval_words_are_feedback(self) -> None:
        """Approval keywords are treated as feedback — approvals use label changes only."""
        assert classify_comment("Approved") == CommentType.FEEDBACK
        assert classify_comment("LGTM") == CommentType.FEEDBACK
        assert classify_comment("looks good to me") == CommentType.FEEDBACK
        assert classify_comment("looks good") == CommentType.FEEDBACK

    def test_feedback_with_question_mark_in_middle(self) -> None:
        """Question mark not at the start should NOT be a question."""
        assert classify_comment("What about this? Add more") == CommentType.FEEDBACK
        assert classify_comment("Is this correct? Please check") == CommentType.FEEDBACK

    def test_feedback_with_question_mark_only_in_middle(self) -> None:
        """A sentence with ? in the middle is feedback."""
        assert classify_comment("Add this feature? Maybe later") == CommentType.FEEDBACK

    # Empty/whitespace tests
    def test_empty_comment_is_feedback(self) -> None:
        """Empty comments should be classified as feedback."""
        assert classify_comment("") == CommentType.FEEDBACK

    def test_whitespace_only_comment_is_feedback(self) -> None:
        """Whitespace-only comments should be classified as feedback."""
        assert classify_comment("   ") == CommentType.FEEDBACK
        assert classify_comment("\n\t") == CommentType.FEEDBACK

    # Edge cases
    def test_question_mark_with_leading_whitespace(self) -> None:
        """Question mark with leading whitespace should be a question."""
        assert classify_comment("  ?Why REST?") == CommentType.QUESTION

    def test_forge_ask_with_leading_whitespace(self) -> None:
        """@forge ask with leading whitespace should be a question."""
        assert classify_comment("  @forge ask explain") == CommentType.QUESTION

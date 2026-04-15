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

    # Approval detection tests
    def test_approval_with_approved_keyword(self) -> None:
        """Comments containing 'approved' should be approvals."""
        assert classify_comment("Approved") == CommentType.APPROVAL
        assert classify_comment("approved") == CommentType.APPROVAL
        assert classify_comment("APPROVED") == CommentType.APPROVAL

    def test_approval_with_lgtm(self) -> None:
        """Comments containing 'lgtm' should be approvals."""
        assert classify_comment("LGTM") == CommentType.APPROVAL
        assert classify_comment("lgtm") == CommentType.APPROVAL
        assert classify_comment("Lgtm") == CommentType.APPROVAL

    def test_approval_with_looks_good_to_me(self) -> None:
        """Comments containing 'looks good to me' should be approvals."""
        assert classify_comment("looks good to me") == CommentType.APPROVAL
        assert classify_comment("Looks good to me!") == CommentType.APPROVAL

    def test_approval_with_looks_good(self) -> None:
        """Comments containing 'looks good' should be approvals."""
        assert classify_comment("looks good") == CommentType.APPROVAL
        assert classify_comment("Looks Good") == CommentType.APPROVAL

    def test_approval_in_sentence(self) -> None:
        """Approval keywords in the middle of a comment should still be approvals."""
        assert classify_comment("This is approved") == CommentType.APPROVAL
        assert classify_comment("I think this looks good") == CommentType.APPROVAL

    # Feedback tests (default)
    def test_feedback_as_default(self) -> None:
        """Comments without question or approval markers should be feedback."""
        assert classify_comment("Please add more detail") == CommentType.FEEDBACK
        assert classify_comment("Can you expand on this section") == CommentType.FEEDBACK

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

    def test_question_takes_precedence_over_approval(self) -> None:
        """If both question marker and approval word exist, question wins."""
        assert classify_comment("?approved") == CommentType.QUESTION
        assert classify_comment("@forge ask is this approved") == CommentType.QUESTION

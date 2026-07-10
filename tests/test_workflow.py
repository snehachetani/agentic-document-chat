import pytest

from src.api.chat import ChatRequest, chat
from src.changes.store import InvalidChangeStateError, change_store
from src.documents.store import get_document_store
from src.rag.summarizer import summarize_section


def test_accepting_change_updates_section_and_history(temp_database) -> None:
    store = get_document_store()
    original = store.get_section("cloud_formation")
    proposed_text = "Clouds form when rising moist air cools and water vapor condenses."

    proposal = change_store.create(
        section_id=original.section_id,
        original_text=original.content,
        proposed_text=proposed_text,
        reason_for_change="Test proposal",
    )

    unchanged = store.get_section("cloud_formation")
    assert unchanged.content == original.content
    assert unchanged.version == original.version

    accepted, new_version = change_store.accept(proposal.change_id)

    updated = store.get_section("cloud_formation")
    assert accepted.status == "accepted"
    assert new_version == original.version + 1
    assert updated.content == proposed_text
    assert updated.version == original.version + 1
    assert updated.history[-1].content == original.content
    assert updated.history[-1].change_id == proposal.change_id

    with pytest.raises(InvalidChangeStateError):
        change_store.accept(proposal.change_id)


def test_rejecting_change_does_not_modify_section(temp_database) -> None:
    store = get_document_store()
    original = store.get_section("cloud_classification")

    proposal = change_store.create(
        section_id=original.section_id,
        original_text=original.content,
        proposed_text="A rejected replacement.",
        reason_for_change="Test rejection",
    )

    rejected = change_store.reject(proposal.change_id)
    unchanged = store.get_section("cloud_classification")

    assert rejected.status == "rejected"
    assert unchanged.content == original.content
    assert unchanged.version == original.version


def test_summary_uses_current_sqlite_section_after_accept(temp_database) -> None:
    store = get_document_store()
    original = store.get_section("condensation_nuclei")
    proposed_text = "Unique accepted text about condensation nuclei."

    proposal = change_store.create(
        section_id=original.section_id,
        original_text=original.content,
        proposed_text=proposed_text,
        reason_for_change="Test current summary source",
    )
    change_store.accept(proposal.change_id)

    result = summarize_section("condensation_nuclei")

    assert "Unique accepted text" in result["summary"]
    assert result["created_change_proposal"] is False
    assert result["external_tools_used"] == []


def test_chat_evidence_request_can_infer_relevant_section(temp_database) -> None:
    response = chat(
        ChatRequest(
            document_id="clouds_doc_v1",
            message="Find evidence for the claim that clouds affect climate.",
        )
    )

    assert response.created_change_proposal is False
    assert response.external_tools_used
    assert response.sources[0]["section_id"] == "clouds_climate_change"
    assert response.evidence_used

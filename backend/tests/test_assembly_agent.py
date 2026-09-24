from models.schemas import GeneratedSection, ProposalOutput
from services.agents.assembly_agent import human_input_checklist


def test_human_input_checklist_flags_methodology_decisions():
    output = ProposalOutput(
        topic="Study",
        sections=[GeneratedSection(section_name="methodology", text="The study uses interviews with participants.")],
    )
    assert any("interview" in item for item in human_input_checklist(output))
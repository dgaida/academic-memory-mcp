import pytest

from mcp_university.summarizer.profiler import PersonProfiler

@pytest.fixture
def profiler():
    p = PersonProfiler()
    return p

def test_profiling_prompt_excludes_student_if_kg_info_present(profiler):
    """Verifies that the prompt contains instructions to exclude 'Studierender' if kg_info exists."""
    email = "staff@th-koeln.de"
    kg_context = "Informationen aus dem Wissensgraphen: Fakultät 10, Institut für Informatik."
    new_content = "Einige E-Mails..."
    existing_profile = ""
    honorific = "Sie"

    prompt = profiler._get_profiling_prompt(email, new_content, existing_profile, honorific, kg_context)

    assert "WICHTIG" in prompt
    assert "NICHT um einen Studierenden" in prompt
    assert "schließe die Rolle \"Studierender\" aus" in prompt

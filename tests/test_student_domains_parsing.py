"""Tests to verify the student domains parsing logic mimicking the VBA macro behavior."""

def simulate_vba_load_student_domains(file_content: str) -> str:
    lines = file_content.splitlines()
    result = []

    for line in lines:
        line = line.strip()

        # Ignore empty lines, headings and comments
        if len(line) > 0 and not line.startswith("#") and not line.startswith("//") and not line.startswith("<!--"):

            # Strip markdown list markers: "-", "*", "+"
            if line.startswith("- "):
                line = line[2:].strip()
            elif line.startswith("* "):
                line = line[2:].strip()
            elif line.startswith("+ "):
                line = line[2:].strip()

            # Strip backticks at start and end
            if line.startswith("`"):
                line = line[1:]
            if line.endswith("`"):
                line = line[:-1]
            line = line.strip()

            # Replace escaped underscores "\" with normal underscores "_"
            line = line.replace("\\_", "_")

            # Convert to lowercase
            line = line.lower()

            if len(line) > 0:
                result.append(line)

    return "|".join(result) if result else "@smail.th-koeln.de|@smail.fh-koeln.de"


def test_vba_student_domains_parsing():
    # Test 1: Standard domain config
    content_1 = """# Studentische Domains
@smail.th-koeln.de
@smail.fh-koeln.de
"""
    assert simulate_vba_load_student_domains(content_1) == "@smail.th-koeln.de|@smail.fh-koeln.de"

    # Test 2: List markers and escaped underscores
    content_2 = """# Studentische Domains
- @smail.th-koeln.de
- @smail.fh-koeln.de
- hans\\_dieter.mueller@th-koeln.de
- hans.werner\\_mueller@th-koeln.de
"""
    assert simulate_vba_load_student_domains(content_2) == "@smail.th-koeln.de|@smail.fh-koeln.de|hans_dieter.mueller@th-koeln.de|hans.werner_mueller@th-koeln.de"

    # Test 3: Other markdown list markers and backticks
    content_3 = """
* @smail.th-koeln.de
+ `hans_dieter.mueller@th-koeln.de`
// some comment line
<!-- another comment -->
"""
    assert simulate_vba_load_student_domains(content_3) == "@smail.th-koeln.de|hans_dieter.mueller@th-koeln.de"

    # Test 4: Empty config falls back to default
    content_4 = ""
    assert simulate_vba_load_student_domains(content_4) == "@smail.th-koeln.de|@smail.fh-koeln.de"

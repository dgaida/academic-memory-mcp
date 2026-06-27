from mcp_university.classifier.sort_emails import extract_lastname

cases = [
    "A B C D <a_b.c_d@smail.th-koeln.de>",
    "TH Köln <nils_karl.mode@smail.th-koeln.de>",
    "Praxissemestersystem der F10 <praxissemester-inf@f10.th-koeln.de>",
    "Wester Helmut <HWester@tuev.com>"
]

for c in cases:
    print(f"Input: {c}")
    print(f"Extracted: {extract_lastname(c)}")
    print("-" * 20)

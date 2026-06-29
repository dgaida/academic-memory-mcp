import re

def normalize_name(name: str) -> str:
    """Normalizes the name by replacing umlauts.

    Args:
        name (str): The name to normalize.

    Returns:
        str: The normalized name.
    """
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss"
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name

def extract_lastname(name_str: str) -> str:
    """Extracts the lastname from a name string.

    Args:
        name_str (str): The string to extract from.

    Returns:
        str: The extracted lastname.
    """
    if not name_str or name_str == "(No Sender)" or name_str == "(No Receiver)":
        return "Unknown"

    # Suche nach E-Mail-Adresse
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", name_str)
    email = email_match.group(0) if email_match else None

    # Fallback für Namen ohne E-Mail Adresse
    clean_name = name_str.split("<")[0].strip().strip("'\"")

    if email:
        local_part = email.split("@")[0]
        if "." in local_part:
            # Rule: after first dot
            lastname_part = local_part.split(".", 1)[1]
            parts = re.split(r'[._]', lastname_part)
            res = "_".join(p[0].upper() + p[1:] for p in parts if p)
            return normalize_name(res)

        # If no dot in email, check if we have a good display name
        if clean_name and (" " in clean_name or "," in clean_name):
            # Use display name instead of a potentially single-word email local part (like 'max')
            pass
        else:
            # Rule: no dot, use everything before @
            lastname_part = local_part
            parts = re.split(r'[._]', lastname_part)
            res = "_".join(p[0].upper() + p[1:] for p in parts if p)
            return normalize_name(res)

    # Display name parsing
    if "," in clean_name:
        # Format: Lastname, Firstname
        res = clean_name.split(",")[0].strip()
        return normalize_name(res)
    elif " " in clean_name:
        # Format: Firstname Lastname
        parts = clean_name.split()
        res = parts[-1].strip()
        return normalize_name(res)
    elif clean_name:
        return normalize_name(clean_name)

    return "Unknown"

if __name__ == "__main__":
    test_cases = [
        ("max.mustermann@smail.th-koeln.de", "Mustermann"),
        ("max.mustermann_schmidt@smail.th-koeln.de", "Mustermann_Schmidt"),
        ("max.mustermann.extra@smail.th-koeln.de", "Mustermann_Extra"),
        ("mustermann@gmail.com", "Mustermann"),
        ("Max Mustermann <max.mustermann@smail.th-koeln.de>", "Mustermann"),
        ("max_mustermann@smail.th-koeln.de", "Max_Mustermann"),
        ("Erika.Mustermann-Schmidt@web.de", "Mustermann-Schmidt"),
        ("erika@web.de", "Erika"),
        ("Erika Mustermann", "Mustermann"),
        ("Max Mustermann <max@example.com>", "Mustermann"), # The one that failed in CI
    ]

    all_passed = True
    for input_str, expected in test_cases:
        result = extract_lastname(input_str)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status} | Input: {input_str:45} | Expected: {expected:20} | Result: {result}")
        if result != expected:
            all_passed = False

    if all_passed:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed.")

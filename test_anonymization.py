import logging
from mcp_university.utils.anonymizer import Anonymizer

logging.basicConfig(level=logging.INFO)

def test_anonymizer():
    # We mock the Ollama client for the test if possible,
    # but here we can just check if the logic in the class works.
    # Note: the actual LLM call won't work without a running Ollama,
    # but the fallback and mapping logic should be testable.

    anon = Anonymizer()
    text = "Hallo Daniel Gaida, ich bin Erika Mustermann (erika.mustermann@web.de). Können wir uns treffen?"

    # Simulate LLM failure or just use the fallback by providing a non-existent model if needed
    # but let's just see if we can instantiate it and check the mapping.

    sender_name = "Erika Mustermann"
    sender_email = "erika.mustermann@web.de"

    # We manually trigger the fallback for this test by mocking the client call or just relying on failure
    print("Testing Anonymization Fallback...")
    anon_text = anon.anonymize(text, sender_name, sender_email)
    print(f"Anonymized: {anon_text}")

    print("Testing De-anonymization...")
    deanon_text = anon.deanonymize_text(anon_text)
    print(f"De-anonymized: {deanon_text}")

    if "Max Mustermann" in anon_text and "erika.mustermann@web.de" not in anon_text:
        print("Anonymization SUCCESS")

    if deanon_text == text:
        print("De-anonymization SUCCESS")

if __name__ == "__main__":
    test_anonymizer()

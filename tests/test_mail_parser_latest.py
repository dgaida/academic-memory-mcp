from mcp_university.parser.mail_parser import MailParser

def test_extract_latest_message_standard():
    parser = MailParser()
    text = """Hallo, hier ist meine Antwort.

Zitat von daniel.gaida@th-koeln.de:
> Alte Mail"""
    latest = parser.extract_latest_message(text)
    assert latest == "Hallo, hier ist meine Antwort."

def test_extract_latest_message_reply_below_quote():
    parser = MailParser()
    text = """Zitat von daniel.gaida@th-koeln.de:

> Guten Tag Herr ...,
>
> gerne biete ich Ihnen einige Terminvorschläge an.
>
> Viele Grüße,
> Daniel Gaida

Ich würde gerne den Termin am Mo, 2026-06-01 13:30-14:00 wahrnehmen."""

    latest = parser.extract_latest_message(text)
    # This currently fails because it breaks at the first line
    assert latest == "Ich würde gerne den Termin am Mo, 2026-06-01 13:30-14:00 wahrnehmen."

def test_extract_latest_message_with_multiple_quotes():
    parser = MailParser()
    text = """Hier ist meine neue Antwort.

Am 01.01.2024 um 10:00 schrieb student@smail.th-koeln.de:
> Alte Antwort
>
> -------- Weitergeleitete Nachricht --------
> Von: daniel.gaida@th-koeln.de
> Datum: 01.01.2024"""
    latest = parser.extract_latest_message(text)
    assert latest == "Hier ist meine neue Antwort."

from mcp_university.parser.mail_parser import MailParser

def test_extract_latest_message_standard():
    parser = MailParser()
    text = """Hallo, hier ist meine Antwort.
Zweite Zeile für den Test.

Zitat von daniel.gaida@th-koeln.de:
> Alte Mail"""
    latest = parser.extract_latest_message(text)
    assert "Hallo, hier ist meine Antwort." in latest
    assert "Zweite Zeile" in latest
    assert "Zitat von" not in latest

def test_extract_latest_message_reply_below_quote():
    parser = MailParser()
    text = """Zitat von daniel.gaida@th-koeln.de:

> Guten Tag Herr ...,
>
> gerne biete ich Ihnen einige Terminvorschläge an.
>
> Viele Grüße,
> Daniel Gaida

Ich würde gerne den Termin am Mo, 2026-06-01 13:30-14:00 wahrnehmen.
Beste Grüße!"""

    latest = parser.extract_latest_message(text)
    assert "Ich würde gerne den Termin" in latest
    assert "Beste Grüße!" in latest
    assert "Guten Tag Herr" not in latest

def test_extract_latest_message_with_multiple_quotes():
    parser = MailParser()
    text = """Hier ist meine neue Antwort.
Und noch mehr Text.

Am 01.01.2024 um 10:00 schrieb student@smail.th-koeln.de:
> Alte Antwort
>
> -------- Weitergeleitete Nachricht --------
> Von: daniel.gaida@th-koeln.de
> Datum: 01.01.2024"""
    latest = parser.extract_latest_message(text)
    assert "Hier ist meine neue Antwort." in latest
    assert "Und noch mehr Text." in latest
    assert "Alte Antwort" not in latest

def test_extract_latest_message_no_fallback_on_clear_marker():
    parser = MailParser()
    text = """Short reply.
Zitat von daniel.gaida@th-koeln.de:
> Quote"""
    latest = parser.extract_latest_message(text)
    # Even if only 1 line, we should NOT fall back because Zitat von is a clear marker.
    assert latest == "Short reply."

def test_extract_latest_message_no_fallback_on_quotes():
    parser = MailParser()
    text = """Short.
> Quote line 1
> Quote line 2"""
    latest = parser.extract_latest_message(text)
    # 2 quotes is also a clear marker.
    assert latest == "Short."

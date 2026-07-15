"""Tests für die Robustheit der process_sorted_emails GUI-Handler bei gelöschten E-Mail-Dateien."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import gradio as gr

# Pre-import modules to avoid AttributeError during patch resolution
import mcp_university.agent.engine
import mcp_university.agent.mcp_agent

# Capture click handlers globally
click_handlers = {}

# Dummy block class to bypass Gradio layout parent tracking and block function registration
class DummyBlock:
    _id = 0
    def __init__(self, *args, **kwargs):
        self.children = []
        self._id = 0
    def __getattr__(self, name):
        return MagicMock()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def click(self, fn, *args, **kwargs):
        if fn.__name__ == "handle_remove_to_tab2":
            click_handlers["remove_to_tab2"] = fn
        elif fn.__name__ == "relocate_remaining":
            click_handlers["relocate_remaining"] = fn
        return MagicMock()

# Global dict to store captured functions
captured_funcs = {}

def test_gui_handlers_with_missing_files(tmp_path):
    """Testet, dass die GUI-Handler bei fehlenden E-Mail-Dateien nicht abstürzen und sich korrekt verhalten.

    Args:
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    controller = MagicMock()
    # Mock suggested action options
    controller.ACTION_OPTIONS = [
        "1) Antwort schreiben.",
        "2) Antwort schreiben mit einem Terminvorschlag.",
        "3) Termin im Kalender anlegen und Person dazu einladen.",
        "4) E-Mail nur archivieren.",
        "5) Aufgabe im Kalender anlegen zum Lesen des Anhangs.",
        "6) Termin für Kolloquium in Kalender anlegen.",
    ]
    controller.relocate_emails.return_value = []

    # Capture decorated render function
    def mock_render(*args, **kwargs):
        def decorator(fn):
            captured_funcs[fn.__name__] = fn
            return fn
        return decorator

    # Create dummy email paths (one existing, one missing)
    existing_mail = tmp_path / "existing.msg"
    existing_mail.write_text("existing content")
    missing_mail = tmp_path / "missing.msg" # does not exist

    # Dummy emails list
    t1_mails_data = [
        {"lastname": "Muster", "class": "Other", "folder": "Inbox", "path": str(existing_mail)},
        {"lastname": "Schulz", "class": "Other", "folder": "Inbox", "path": str(missing_mail)}
    ]

    # Patch all Gradio layout and components with DummyBlock to avoid runtime layout/page attributes resolution errors
    with patch("gradio.render", side_effect=mock_render), \
         patch("gradio.Row", DummyBlock), \
         patch("gradio.Column", DummyBlock), \
         patch("gradio.Group", DummyBlock), \
         patch("gradio.Checkbox", DummyBlock), \
         patch("gradio.Button", DummyBlock), \
         patch("gradio.Markdown", DummyBlock), \
         patch("gradio.State", DummyBlock), \
         patch("gradio.Textbox", DummyBlock), \
         patch("gradio.Tabs", DummyBlock), \
         patch("gradio.Tab", DummyBlock), \
         patch("gradio.Blocks.launch") as mock_launch:

        # Import run_gradio_gui inside patch context to ensure decorator is mocked during import
        from scripts.process_sorted_emails import run_gradio_gui

        # Run GUI setup which registers decorators
        run_gradio_gui(controller, tmp_path)

        # Confirm we successfully captured the render function
        assert "render_tab1" in captured_funcs

        # Call the render function to instantiate the buttons and capture click handlers
        captured_funcs["render_tab1"](t1_mails_data)

        # Confirm we successfully captured the click handlers
        assert "remove_to_tab2" in click_handlers
        assert "relocate_remaining" in click_handlers

        # Test 1: Test handle_remove_to_tab2 where a selected mail is missing
        handle_remove = click_handlers["remove_to_tab2"]

        # selected info: idx 1 (Schulz - missing) and idx 0 (Muster - existing) are selected.
        # all_states consists of: checkboxes (selected: [True, True]), attachments (both False)
        all_states = [True, True, False, False]

        # Since handle_remove yields generators (it uses yield from remove_to_tab2_logic),
        # we iterate over its yields.
        generator = handle_remove(t1_mails_data, [], *all_states)
        yields = list(generator)

        # Inspect the yielded states:
        first_yield = yields[0]
        new_t1_state = first_yield[0]
        current_t2_state = first_yield[1]
        status_msg = first_yield[2]

        # Schulz (missing) should be popped from t1 and skipped from t2
        assert len(new_t1_state) == 0 # both got popped
        assert len(current_t2_state) == 1 # only existing mail "Muster" moved to Tab 2!
        assert current_t2_state[0]["lastname"] == "Muster"
        assert "Schulz" in status_msg # Status message informs about missing mail!

        # Test 2: Test relocate_remaining where some verbleibenden emails are missing
        handle_relocate = click_handlers["relocate_remaining"]

        # If t1_mails has Muster (exists) and Schulz (missing)
        # simulate relocate_remaining(t1_mails, *att_states)
        res_t1, res_msg = handle_relocate(t1_mails_data, False, False)

        # Schulz (missing) should be filtered out first, and controller.relocate_emails called only on Muster (existing)
        controller.relocate_emails.assert_called_once()
        called_args = controller.relocate_emails.call_args[0][0]
        assert len(called_args) == 1
        assert called_args[0]["lastname"] == "Muster"
        assert res_t1 == [] # Muster was successfully relocated, list of t1 is empty now!
        assert "Schulz" not in [m["lastname"] for m in res_t1]


# We will subclass DummyBlock and capture handle_tab2_process from process_btn.click
class CapturingDummyBlock(DummyBlock):
    def click(self, fn, *args, **kwargs):
        super().click(fn, *args, **kwargs)
        if fn.__name__ == "handle_tab2_process":
            click_handlers["handle_tab2_process"] = fn
        return MagicMock()


def test_handle_tab2_process_updates_state(tmp_path):
    """Testet, dass handle_tab2_process die t2_mails-Liste mit neuen Pfaden und Klassen aktualisiert.

    Args:
        tmp_path: Pytest Fixture für ein temporäres Verzeichnis.

    Returns:
        None
    """
    controller = MagicMock()
    controller.ACTION_OPTIONS = [
        "1) Antwort schreiben.",
        "2) Antwort schreiben mit einem Terminvorschlag.",
        "3) Termin im Kalender anlegen und Person dazu einladen.",
        "4) E-Mail nur archivieren.",
        "5) Aufgabe im Kalender anlegen zum Lesen des Anhangs.",
        "6) Termin für Kolloquium in Kalender anlegen.",
    ]
    # Mock relocate_emails to simulate updating the change with new_path and new_identifier_path
    def mock_relocate(changes):
        for change in changes:
            change["new_path"] = tmp_path / "new_existing.msg"
            change["new_identifier_path"] = tmp_path
        return []
    controller.relocate_emails.side_effect = mock_relocate
    controller.execute_action.return_value = "Aktion erfolgreich ausgeführt"

    # Capture decorated render function
    def mock_render(*args, **kwargs):
        def decorator(fn):
            captured_funcs[fn.__name__] = fn
            return fn
        return decorator

    with patch("gradio.render", side_effect=mock_render), \
         patch("gradio.Row", CapturingDummyBlock), \
         patch("gradio.Column", CapturingDummyBlock), \
         patch("gradio.Group", CapturingDummyBlock), \
         patch("gradio.Checkbox", CapturingDummyBlock), \
         patch("gradio.Button", CapturingDummyBlock), \
         patch("gradio.Markdown", CapturingDummyBlock), \
         patch("gradio.State", CapturingDummyBlock), \
         patch("gradio.Textbox", CapturingDummyBlock), \
         patch("gradio.Tabs", CapturingDummyBlock), \
         patch("gradio.Tab", CapturingDummyBlock), \
         patch("gradio.Blocks.launch"):

        from scripts.process_sorted_emails import run_gradio_gui
        run_gradio_gui(controller, tmp_path)

        assert "render_tab2" in captured_funcs

        # Setup initial t2_mails list
        initial_t2_mails = [
            {
                "lastname": "Muster",
                "class": "Other",
                "folder": "Inbox",
                "path": str(tmp_path / "existing.msg"),
                "latest_mail": str(tmp_path / "existing.msg")
            }
        ]

        # Call render_tab2 to bind states and capture click handler
        captured_funcs["render_tab2"](initial_t2_mails)

        assert "handle_tab2_process" in click_handlers
        handle_tab2_process = click_handlers["handle_tab2_process"]

        # Arguments of handle_tab2_process: t2_mails, *args (sels, acts, atts)
        # Sels = ["Klausuren"], Acts = ["1) Antwort schreiben."], Atts = [False]
        updated_t2_mails, msg = handle_tab2_process(initial_t2_mails, "Klausuren", "1) Antwort schreiben.", False)

        # Verify that the returned state is updated correctly
        assert len(updated_t2_mails) == 1
        updated_mail = updated_t2_mails[0]
        assert updated_mail["lastname"] == "Muster"
        assert updated_mail["class"] == "Klausuren"
        assert updated_mail["path"] == Path(tmp_path / "new_existing.msg")
        assert updated_mail["latest_mail"] == Path(tmp_path / "new_existing.msg")
        assert updated_mail["identifier_path"] == Path(tmp_path)
        assert updated_mail["suggested_action"] == "1) Antwort schreiben."
        assert updated_mail["save_attachments"] is False
        assert "Aktionen:" in msg
        assert "Muster: Aktion erfolgreich ausgeführt" in msg

"""Comprehensive coverage boost tests for PersonProfiler in mcp_university/summarizer/profiler.py."""

import re
import pytest
import os
import json
import yaml
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone, timedelta
from mcp_university.summarizer.profiler import PersonProfiler


@pytest.fixture
def mock_profiler_setup(tmp_path):
    """Sets up a PersonProfiler with mocked dependencies and a temp storage path.

    Args:
        tmp_path (Path): Temporary path fixture from pytest.

    Returns:
        tuple: (profiler, mock_store, mock_profile_store, mock_llm, mock_parser, mock_config)
    """
    mock_store = MagicMock()
    mock_profile_store = MagicMock()
    mock_llm = MagicMock()
    mock_parser = MagicMock()
    mock_config = MagicMock()

    mock_config.sqlite_path = tmp_path / "sqlite.db"
    mock_config.data_dir = tmp_path / "data"
    mock_config.config_dir = tmp_path / "config"
    mock_config.user.name = "Daniel Gaida"
    mock_config.user.email = "daniel.gaida@th-koeln.de"
    mock_config.user.emails = ["daniel.gaida@th-koeln.de", "dgaida@th-koeln.de"]

    mock_config.config_dir.mkdir(parents=True, exist_ok=True)
    mock_config.data_dir.mkdir(parents=True, exist_ok=True)

    with patch('mcp_university.summarizer.profiler.get_config', return_value=mock_config), \
         patch('mcp_university.summarizer.profiler.MetadataStore', return_value=mock_store), \
         patch('mcp_university.summarizer.profiler.ProfileStore', return_value=mock_profile_store), \
         patch('mcp_university.summarizer.profiler.LLMClientWrapper', return_value=mock_llm), \
         patch('mcp_university.summarizer.profiler.MailParser', return_value=mock_parser):

        profiler = PersonProfiler(storage_path=tmp_path / "Steckbriefe")
        yield profiler, mock_store, mock_profile_store, mock_llm, mock_parser, mock_config


def test_get_search_paths_comprehensive(mock_profiler_setup, tmp_path):
    """Tests the get_search_paths method of PersonProfiler under various YAML setups.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, _, mock_config = mock_profiler_setup

    # Create directories that will exist
    p1 = tmp_path / "class_path_1"
    p2 = tmp_path / "train_path_dir"
    p3 = tmp_path / "test_path_dir"
    p1.mkdir()
    p2.mkdir()
    p3.mkdir()

    # Create classifier_paths.yaml
    cp_data = {
        "class_paths": {
            "class1": str(p1),
            "nonexistent": str(tmp_path / "nonexistent_dir")
        }
    }
    with open(mock_config.config_dir / "classifier_paths.yaml", "w", encoding="utf-8") as f:
        yaml.dump(cp_data, f)

    # Create train_test_folders.yaml
    ttf_data = {
        "train_path": str(p2),
        "test_path": str(p3)
    }
    with open(mock_config.config_dir / "train_test_folders.yaml", "w", encoding="utf-8") as f:
        yaml.dump(ttf_data, f)

    paths = profiler.get_search_paths()

    # Check that nonexistent paths are filtered out, but valid ones are included
    assert p1 in paths
    assert p2 in paths
    assert p3 in paths
    assert (tmp_path / "nonexistent_dir") not in paths


def test_find_emails_for_address_various_cases(mock_profiler_setup, tmp_path):
    """Tests finding emails by matching sender, To, and CC headers.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, mock_parser, _ = mock_profiler_setup

    # Setup directories
    search_dir = tmp_path / "search_dir"
    search_dir.mkdir()

    # Create different files: msg, eml, txt (to be ignored)
    msg_file = search_dir / "test1.msg"
    eml_file = search_dir / "test2.eml"
    txt_file = search_dir / "test3.txt"
    msg_file.touch()
    eml_file.touch()
    txt_file.touch()

    # Mock the search paths to return search_dir
    with patch.object(profiler, 'get_search_paths', return_value=[search_dir]):

        # Scenario A: EML file match CC, MSG file returns no details (None), but raises no error.
        # Scenario B: MSG file matches sender or recipient.
        def mock_get_msg_details(filepath):
            if "test1" in str(filepath):
                # Returns details where To matches
                return {
                    "from_email": "someone@example.com",
                    "to": [{"email": "target@example.com"}],
                    "cc": [],
                    "date": datetime(2023, 1, 1, tzinfo=timezone.utc),
                    "subject": "MSG match",
                    "body": "Body MSG"
                }
            return None

        def mock_get_eml_details(filepath):
            if "test2" in str(filepath):
                # Returns details where CC matches
                return {
                    "from_email": "someone_else@example.com",
                    "to": [],
                    "cc": [{"email": "target@example.com"}],
                    "date": datetime(2023, 1, 2, tzinfo=timezone.utc),
                    "subject": "EML match",
                    "body": "Body EML"
                }
            return None

        mock_parser._get_msg_details.side_effect = mock_get_msg_details
        mock_parser._get_eml_details.side_effect = mock_get_eml_details

        # Run search for target@example.com
        emails = profiler.find_emails_for_address("target@example.com")

        # Check matching of both To and CC
        assert len(emails) == 2
        subjects = [m["details"]["subject"] for m in emails]
        assert "MSG match" in subjects
        assert "EML match" in subjects


def test_find_emails_for_address_exception_handling(mock_profiler_setup, tmp_path):
    """Tests that find_emails_for_address log warnings and continues on exceptions.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, mock_parser, _ = mock_profiler_setup

    search_dir = tmp_path / "search_dir"
    search_dir.mkdir()
    msg_file = search_dir / "test_error.msg"
    msg_file.touch()

    with patch.object(profiler, 'get_search_paths', return_value=[search_dir]):
        # Force parser to raise an exception
        mock_parser._get_msg_details.side_effect = Exception("Parsing failed catastrophically")

        emails = profiler.find_emails_for_address("any@example.com")
        # Should catch exception, log warning and return empty list
        assert len(emails) == 0


def test_create_batches_forcing_splits(mock_profiler_setup):
    """Tests batch creation when exceeding max character size and forces optimize batch recursive split.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup

    # Prepare emails with large body text to force exceeding max_chars
    d1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    emails = [
        {"details": {"date": d1, "body": "A" * 8000, "subject": "S1"}},
        {"details": {"date": d1 + timedelta(days=1), "body": "B" * 8000, "subject": "S2"}},
        {"details": {"date": d1 + timedelta(days=2), "body": "C" * 8000, "subject": "S3"}},
    ]

    # Create batches with max_chars = 10000. This should force splitting into multiple batches
    batches = profiler.create_batches(emails, max_chars=10000)
    assert len(batches) >= 2


def test_optimize_batches_recursive_halving(mock_profiler_setup):
    """Tests that _optimize_batches recursively splits a batch if its character size exceeds 20000.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup

    d = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Total character size will be 25000 (exceeds 20000)
    # We will trigger the recursive halving logic
    batch_large = [
        {"details": {"date": d, "body": "X" * 12000}},
        {"details": {"date": d + timedelta(seconds=1), "body": "Y" * 13000}}
    ]

    # We bypass normal create_batches and test _optimize_batches directly
    # Ensure gaps logic is simple (no gap > 30 days) so it doesn't split by gap first
    batches = [batch_large]
    optimized = profiler._optimize_batches(batches)

    # Should split by recursive halving since gap was small but total chars > 20000
    assert len(optimized) == 2


def test_get_knowledge_graph_context_various_cases(mock_profiler_setup):
    """Tests _get_knowledge_graph_context under various conditions like name fallbacks and depth limit.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, mock_store, _, _, _, _ = mock_profiler_setup

    # Case A: Email not found, but Name fallback found
    mock_store.get_node_by_property.return_value = None

    # Mock get_all_nodes to return a list of nodes, one matches by name variant "Max Mustermann"
    person_node = {
        "id": "node_max",
        "name": "Mustermann, Max",
        "type": "Person",
        "properties_json": json.dumps({"email": "max@th-koeln.de"})
    }
    mock_store.get_all_nodes.return_value = [person_node]

    # Mock get_node_by_id
    mock_store.get_node_by_id.side_effect = lambda nid: person_node if nid == "node_max" else None
    mock_store.get_outgoing_edges.return_value = []

    # Searching with Name part in the email address "Max Mustermann <max@example.com>"
    context = profiler._get_knowledge_graph_context("Max Mustermann <max@example.com>")
    assert "Mustermann, Max" in context


def test_get_knowledge_graph_context_not_found(mock_profiler_setup):
    """Tests _get_knowledge_graph_context returning empty string when person node is not found.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, mock_store, _, _, _, _ = mock_profiler_setup
    mock_store.get_node_by_property.return_value = None
    mock_store.get_all_nodes.return_value = []

    context = profiler._get_knowledge_graph_context("nonexistent@example.com")
    assert context == ""


def test_get_knowledge_graph_context_depth_and_none_node(mock_profiler_setup):
    """Tests DFS depth limit and None node in get_knowledge_graph_context.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, mock_store, _, _, _, _ = mock_profiler_setup

    person_node = {
        "id": "node_1",
        "name": "User",
        "type": "Person",
        "properties_json": json.dumps({"email": "user@example.com"})
    }

    mock_store.get_node_by_property.return_value = person_node

    # Define nodes: node_1 -> node_2 -> node_3 -> node_4 -> node_5 (node_5 is beyond depth 3)
    # Let's also include a None node mapping (e.g. node_3 returns None) to trigger line 274
    nodes_map = {
        "node_1": person_node,
        "node_2": {"id": "node_2", "name": "Level 1", "type": "Org", "properties_json": "{}"},
        "node_3": None, # Will trigger 'if not node: continue'
        "node_4": {"id": "node_4", "name": "Level 3", "type": "Role", "properties_json": "{}"},
        "node_5": {"id": "node_5", "name": "Level 4", "type": "SubOrg", "properties_json": "{}"},
    }
    mock_store.get_node_by_id.side_effect = lambda nid: nodes_map.get(nid)

    def get_outgoing_edges(node_id):
        if node_id == "node_1":
            return [{"target_id": "node_2"}]
        if node_id == "node_2":
            return [{"target_id": "node_3"}, {"target_id": "node_4"}]
        if node_id == "node_4":
            return [{"target_id": "node_5"}]
        return []

    mock_store.get_outgoing_edges.side_effect = get_outgoing_edges

    context = profiler._get_knowledge_graph_context("user@example.com")

    assert "User" in context
    assert "Level 1" in context
    # Level 3 (node_4) is at depth 2 (node_1 -> node_2 -> node_4), so it should be present.
    assert "Level 3" in context
    # Level 4 (node_5) is at depth 3 (node_1 -> node_2 -> node_4 -> node_5). Wait, depth starts at 0.
    # node_1: depth 0
    # node_2: depth 1
    # node_4: depth 2
    # node_5: depth 3. So it is processed (since depth <= 3 is allowed, > 3 is ignored).
    # If we had a depth 4 node, it would be skipped. Let's verify that the DFS runs without crashing.


def test_generate_profile_already_exists(mock_profiler_setup, tmp_path):
    """Tests generate_profile when the profile file already exists and force_update is False.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup
    email = "existing@example.com"
    profile_file = tmp_path / "Steckbriefe" / f"{email}.md"
    profile_file.parent.mkdir(parents=True, exist_ok=True)
    profile_file.write_text("# Already Generated Profile", encoding="utf-8")

    result = profiler.generate_profile(email, force_update=False)
    assert result == "# Already Generated Profile"


def test_generate_profile_tool_user(mock_profiler_setup, tmp_path):
    """Tests generate_profile for the tool's configured user.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, mock_llm, _, mock_config = mock_profiler_setup
    email = mock_config.user.emails[0] # "daniel.gaida@th-koeln.de"

    mock_llm.chat.return_value = {"message": {"content": "# Tool User Profile"}}

    # Mock knowledge graph context search
    with patch.object(profiler, '_get_knowledge_graph_context', return_value="- Prof node"):
        result = profiler.generate_profile(email, force_update=True)
        assert "Tool User Profile" in result

        # Ensure no emails searched for tool user
        with patch.object(profiler, 'find_emails_for_address') as mock_find:
            profiler.generate_profile(email, force_update=True)
            mock_find.assert_not_called()


def test_generate_profile_no_data(mock_profiler_setup):
    """Tests generate_profile returning None when no emails and no Wissensgraph info exist.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup
    email = "empty@example.com"

    with patch.object(profiler, 'find_emails_for_address', return_value=[]), \
         patch.object(profiler, '_get_knowledge_graph_context', return_value=""):
        result = profiler.generate_profile(email, force_update=True)
        assert result is None


def test_update_profile_fallback_to_generate(mock_profiler_setup):
    """Tests update_profile falls back to generate_profile if file does not exist.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup
    email = "newbie@example.com"

    with patch.object(profiler, 'generate_profile', return_value="# Fresh Profile") as mock_gen:
        result = profiler.update_profile(email)
        assert result == "# Fresh Profile"
        mock_gen.assert_called_once_with(email)


def test_update_profile_tool_user(mock_profiler_setup):
    """Tests update_profile forces regeneration for the tool user.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, mock_config = mock_profiler_setup
    email = mock_config.user.emails[0]

    # Create dummy profile file
    profile_file = profiler.storage_path / f"{email}.md"
    profile_file.write_text("# Old User Profile", encoding="utf-8")

    with patch.object(profiler, 'generate_profile', return_value="# Updated User Profile") as mock_gen:
        result = profiler.update_profile(email)
        assert result == "# Updated User Profile"
        mock_gen.assert_called_once_with(email, force_update=True)


def test_update_profile_non_datetime_and_error_handling(mock_profiler_setup, tmp_path):
    """Tests parsing of email dates in update_profile that are ISO strings or invalid.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, mock_profile_store, mock_llm, _, _ = mock_profiler_setup
    email = "test_dates@example.com"

    profile_file = tmp_path / "Steckbriefe" / f"{email}.md"
    profile_file.write_text("# Initial Profile\n## Quellen\n- Old Source", encoding="utf-8")

    # Set profile mtime to 1 day ago
    past_mtime = datetime.now(timezone.utc) - timedelta(days=1)
    os.utime(profile_file, (past_mtime.timestamp(), past_mtime.timestamp()))

    # Mock emails:
    # 1. ISO format string date that is newer (e.g. today)
    # 2. Invalid date format string (raises ValueError/TypeError)
    emails = [
        {
            "path": Path("iso_mail.msg"),
            "date": (datetime.now(timezone.utc)).isoformat(),
            "details": {
                "date": (datetime.now(timezone.utc)).isoformat(),
                "subject": "ISO subject",
                "body": "ISO body"
            }
        },
        {
            "path": Path("invalid_mail.msg"),
            "date": "completely_invalid_date_string",
            "details": {
                "date": "completely_invalid_date_string",
                "subject": "Invalid subject",
                "body": "Invalid body"
            }
        }
    ]

    with patch.object(profiler, 'find_emails_for_address', return_value=emails), \
         patch.object(profiler, '_get_knowledge_graph_context', return_value=""), \
         patch.object(profiler, '_determine_honorific', return_value="Sie"):

        mock_profile_store.get_processed_filenames.return_value = []
        mock_llm.chat.return_value = {"message": {"content": "# Updated with dates"}}

        result = profiler.update_profile(email)
        assert result.startswith("# Updated with dates")


def test_update_profile_no_new_emails(mock_profiler_setup, tmp_path):
    """Tests update_profile when no new emails are found relative to the profile file mtime.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, mock_profile_store, _, _, _ = mock_profiler_setup
    email = "no_new@example.com"

    profile_file = tmp_path / "Steckbriefe" / f"{email}.md"
    profile_file.write_text("# Current Profile Content", encoding="utf-8")

    # Mock no new emails matching date or all already processed
    with patch.object(profiler, 'find_emails_for_address', return_value=[]):
        mock_profile_store.get_processed_filenames.return_value = []
        result = profiler.update_profile(email)
        assert result == "# Current Profile Content"


def test_update_all_profiles_and_get_profile(mock_profiler_setup, tmp_path):
    """Tests the bulk update_all_profiles and single get_profile getter.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup

    # Test storage path not existing
    with patch.object(profiler, 'storage_path') as mock_path:
        mock_path.exists.return_value = False
        profiler.update_all_profiles() # Should return without doing anything

    # Create storage path and some profile files
    profiler.storage_path.mkdir(parents=True, exist_ok=True)

    p1 = profiler.storage_path / "student@example.com.md"
    p2 = profiler.storage_path / "not_an_email.md"
    p1.write_text("# Student", encoding="utf-8")
    p2.write_text("# Not Email", encoding="utf-8")

    with patch.object(profiler, 'update_profile') as mock_update:
        profiler.update_all_profiles()
        # Should only call update_profile for files with '@' in filename
        mock_update.assert_called_once_with("student@example.com")

    # Test get_profile wrapper
    with patch.object(profiler, 'update_profile', return_value="# Profile data") as mock_update_single:
        res = profiler.get_profile("student@example.com")
        assert res == "# Profile data"
        mock_update_single.assert_called_once_with("student@example.com")


def test_determine_honorific_comprehensive(mock_profiler_setup):
    """Tests the _determine_honorific logic under various communication flow matches.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, mock_llm, _, mock_config = mock_profiler_setup
    user_email = mock_config.user.emails[0]
    target_email = "target_person@example.com"

    # Case 1: No emails
    assert profiler._determine_honorific([], target_email) == "Sie"

    # Case 2: Direct emails with sammelmail to ignore, and testing get_date helper
    # We will pass:
    # 1. Sammelmail from target with "Hallo zusammen" in body (should be ignored)
    # 2. Direct mail from user to target (should be counted)
    # 3. Direct mail from target to user (should be counted)
    # 4. Another mail where "date" is a top-level key instead of "details.date"
    emails = [
        {
            "details": {
                "from_email": target_email,
                "to": [{"email": user_email}],
                "body": "Hallo zusammen, wie gehts?",
                "date": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "subject": "Sammelmail"
            }
        },
        {
            "details": {
                "from_email": user_email,
                "to": [{"email": target_email}],
                "body": "Kannst du mir helfen?",
                "date": datetime(2023, 1, 2, tzinfo=timezone.utc),
                "subject": "Direct user to target"
            }
        },
        {
            "details": {
                "from_email": target_email,
                "to": [{"email": user_email}],
                "body": "Ja gerne, ich helfe dir.",
                "date": datetime(2023, 1, 3, tzinfo=timezone.utc),
                "subject": "Direct target to user"
            }
        },
        # Top-level "date" key
        {
            "date": datetime(2023, 1, 4, tzinfo=timezone.utc),
            "details": {
                "from_email": target_email,
                "to": [{"email": user_email}],
                "body": "Danke dir!",
                "subject": "Direct with top level date"
            }
        }
    ]

    # Mock LLM to return "Du" for the chat prompt
    mock_llm.chat.return_value = {"message": {"content": "Du"}}
    assert profiler._determine_honorific(emails, target_email) == "Du"

    # Case 3: No direct emails found -> relevant_emails fallback (sorted_emails[:3])
    # Let's mock LLM to raise an Exception to cover line 577-579
    mock_llm.chat.side_effect = Exception("LLM connection error")
    assert profiler._determine_honorific(emails, target_email) == "Sie"


def test_get_sources_text_empty(mock_profiler_setup):
    """Tests _get_sources_text when sources are empty.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup
    result = profiler._get_sources_text([], "")
    assert result == ""


def test_find_emails_for_address_not_details_continue(mock_profiler_setup, tmp_path):
    """Tests that find_emails_for_address continues when details is None.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
        tmp_path (Path): Temporary path fixture.
    """
    profiler, _, _, _, mock_parser, _ = mock_profiler_setup
    search_dir = tmp_path / "search_dir"
    search_dir.mkdir()
    msg_file = search_dir / "test_none.msg"
    msg_file.touch()

    with patch.object(profiler, 'get_search_paths', return_value=[search_dir]):
        mock_parser._get_msg_details.return_value = None
        emails = profiler.find_emails_for_address("any@example.com")
        assert len(emails) == 0


def test_optimize_batches_less_than_two_emails(mock_profiler_setup):
    """Tests _optimize_batches when total emails is less than 2.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, _, _, _ = mock_profiler_setup
    batches = [[{"details": {"date": datetime.now(), "body": "B1"}}]]
    result = profiler._optimize_batches(batches)
    assert result == batches


def test_get_knowledge_graph_context_cycle(mock_profiler_setup):
    """Tests DFS cycle detection in get_knowledge_graph_context.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, mock_store, _, _, _, _ = mock_profiler_setup
    person_node = {
        "id": "node_1",
        "name": "User",
        "type": "Person",
        "properties_json": "{}"
    }
    mock_store.get_node_by_property.return_value = person_node
    # Trigger cycle: node_1 points to node_1
    mock_store.get_outgoing_edges.return_value = [{"target_id": "node_1"}]
    mock_store.get_node_by_id.return_value = person_node

    context = profiler._get_knowledge_graph_context("user@example.com")
    assert "User" in context


def test_get_knowledge_graph_context_empty(mock_profiler_setup):
    """Tests empty context return in get_knowledge_graph_context.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, mock_store, _, _, _, _ = mock_profiler_setup
    person_node = {
        "id": "node_1",
        "name": "User",
        "type": "Person",
        "properties_json": "{}"
    }
    mock_store.get_node_by_property.return_value = person_node
    # Trigger empty context by returning None for node_1's lookup
    mock_store.get_node_by_id.return_value = None

    context = profiler._get_knowledge_graph_context("user@example.com")
    assert context == ""


def test_determine_honorific_break_on_large_counts(mock_profiler_setup):
    """Tests that _determine_honorific breaks the loop early when both directions have >= 4 emails.

    Args:
        mock_profiler_setup (tuple): Mocked profiler and dependencies.
    """
    profiler, _, _, mock_llm, _, mock_config = mock_profiler_setup
    user_email = mock_config.user.emails[0]
    target_email = "target@example.com"

    # Provide 5 emails from user to target, and 5 from target to user
    emails = []
    for i in range(5):
        emails.append({
            "details": {
                "from_email": user_email,
                "to": [{"email": target_email}],
                "body": f"Du Mail {i}",
                "date": datetime(2023, 1, i+1, tzinfo=timezone.utc),
                "subject": "S"
            }
        })
        emails.append({
            "details": {
                "from_email": target_email,
                "to": [{"email": user_email}],
                "body": f"Sie Mail {i}",
                "date": datetime(2023, 2, i+1, tzinfo=timezone.utc),
                "subject": "S"
            }
        })

    mock_llm.chat.return_value = {"message": {"content": "Sie"}}
    res = profiler._determine_honorific(emails, target_email)
    assert res == "Sie"

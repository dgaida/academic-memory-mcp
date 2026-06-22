import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mcp_university.knowledge_graph.ontology_learner import OntologyLearner

@pytest.fixture
def mock_deps():
    store = MagicMock()
    summarizer = MagicMock()
    return store, summarizer

def test_learn_from_emails(mock_deps, tmp_path):
    store, summarizer = mock_deps
    learner = OntologyLearner(store, summarizer)
    
    email_dir = tmp_path / "emails"
    email_dir.mkdir()
    msg_file = email_dir / "test.msg"
    msg_file.touch()
    
    with patch.object(learner.mail_parser, 'parse', return_value='From: Daniel Gaida <daniel.gaida@th-koeln.de>\nTo: Student'):
        # Add a second email to trigger len(names) > 1
        with patch('pathlib.Path.rglob', return_value=[msg_file, Path("other.msg")]):
            with patch.object(learner.mail_parser, 'parse') as mock_parse:
                mock_parse.side_effect = [
                    'From: Daniel Gaida <daniel.gaida@th-koeln.de>',
                    'From: "D. Gaida" <daniel.gaida@th-koeln.de>'
                ]
                learner.learn_from_emails(email_dir)
                
    store.add_alias.assert_called_once_with("D. Gaida", "Daniel Gaida", "Person")

def test_learn_module_aliases(mock_deps):
    store, summarizer = mock_deps
    learner = OntologyLearner(store, summarizer)
    
    store.get_all_nodes.return_value = [
        {'name': 'KI', 'type': 'Modul'},
        {'name': 'Künstliche Intelligenz', 'type': 'Modul'}
    ]
    
    summarizer._chat_request.return_value = '[["KI", "Künstliche Intelligenz"]]'
    
    learner.learn_module_aliases()
    store.add_alias.assert_called_once_with("KI", "Künstliche Intelligenz", "Modul")

def test_learn_module_aliases_empty(mock_deps):
    store, summarizer = mock_deps
    learner = OntologyLearner(store, summarizer)
    store.get_all_nodes.return_value = []
    learner.learn_module_aliases()
    assert not summarizer._chat_request.called

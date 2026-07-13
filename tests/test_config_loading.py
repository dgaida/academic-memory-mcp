"""Tests for the configuration loading logic."""
from mcp_university.config import UserConfig

def test_user_config_single_email():
    """Test UserConfig with a single email string."""
    data = {
        "name": "Test User",
        "email": "test@example.com"
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.emails == []

def test_user_config_email_list():
    """Test UserConfig with email as a list."""
    data = {
        "name": "Test User",
        "email": ["primary@example.com", "secondary@example.com"]
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "primary@example.com"
    assert user.emails == ["primary@example.com", "secondary@example.com"]

def test_user_config_explicit_emails():
    """Test UserConfig with explicit emails list and single email string."""
    data = {
        "name": "Test User",
        "email": "primary@example.com",
        "emails": ["other@example.com"]
    }
    user = UserConfig(**data)
    assert user.name == "Test User"
    assert user.email == "primary@example.com"
    assert user.emails == ["other@example.com"]

def test_user_config_empty_email_list():
    """Test UserConfig with an empty email list."""
    data = {
        "name": "Test User",
        "email": []
    }
    user = UserConfig(**data)
    assert user.email == ""
    assert user.emails == []


def test_config_sync_vba_macros(tmp_path):
    """Test that loading the Config automatically synchronizes ACCOUNT_NAME in VBA .bas files."""
    from mcp_university.config import Config
    import shutil
    from unittest.mock import patch

    # Create dummy config files
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()

    # user.yaml with custom email
    user_yaml = cfg_dir / "user.yaml"
    user_yaml.write_text("name: 'Test Agent'\nemail: 'custom.agent@th-koeln.de'", encoding="utf-8")

    # dummy files for others
    (cfg_dir / "folders.yaml").write_text("folders: []", encoding="utf-8")
    (cfg_dir / "ontology.yaml").write_text("node_types: []\nedge_types: []", encoding="utf-8")
    (cfg_dir / "models.yaml").write_text("llm:\n  model: 'gemma'\n", encoding="utf-8")

    # Create dummy outlook_macro dir at the same parent level
    macro_dir = tmp_path / "outlook_macro"
    macro_dir.mkdir()

    bas_file = macro_dir / "DummyExport.bas"
    bas_file.write_text('Private Const ACCOUNT_NAME As String = "daniel.gaida@th-koeln.de"', encoding="utf-8")

    # Load Config with custom config_dir
    with patch("mcp_university.config.load_dotenv"):
        config = Config(config_dir=cfg_dir)

    # The bas file should have been synchronized!
    updated_content = bas_file.read_text(encoding="utf-8")
    assert 'Private Const ACCOUNT_NAME As String = "custom.agent@th-koeln.de"' in updated_content

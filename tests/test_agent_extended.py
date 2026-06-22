import pytest
from unittest.mock import MagicMock, patch
from mcp_university.agent.engine import Agent
from pathlib import Path

@pytest.fixture
def mock_cfg():
    cfg = MagicMock()
    cfg.llm.model = "m"
    cfg.llm.base_url = "http://u"
    cfg.data_dir = Path("/tmp")
    cfg.sqlite_path = Path("/tmp/test.db")
    cfg.qdrant_path = Path("/tmp/qdrant")
    cfg.embeddings.model = "em"
    cfg.log_path = Path("/tmp/logs")
    cfg.user.email = "user@example.com"
    return cfg

def test_agent_init(mock_cfg):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),          patch("mcp_university.agent.engine.MetadataStore"),          patch("mcp_university.agent.engine.SearchIndex"),          patch("mcp_university.agent.engine.LLMClientWrapper"),          patch("mcp_university.agent.engine.ParserFactory"):
        
        agent = Agent()
        assert agent.model == "m"
        assert "search_documents" in agent.available_tools

def test_agent_chat(mock_cfg):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),          patch("mcp_university.agent.engine.MetadataStore"),          patch("mcp_university.agent.engine.SearchIndex"),          patch("mcp_university.agent.engine.LLMClientWrapper") as mock_llm,          patch("mcp_university.agent.engine.ParserFactory"):
        
        agent = Agent()
        mock_llm_inst = mock_llm.return_value
        mock_llm_inst.chat.return_value = {"message": {"content": "Response content"}}
        
        res = agent.chat([{"role": "user", "content": "Hello"}])
        assert "Response content" in res

def test_agent_tools(mock_cfg, tmp_path):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),          patch("mcp_university.agent.engine.MetadataStore") as mock_store_cls,          patch("mcp_university.agent.engine.SearchIndex") as mock_idx,          patch("mcp_university.agent.engine.LLMClientWrapper"),          patch("mcp_university.agent.engine.ParserFactory") as mock_pf:
        
        mock_store = mock_store_cls.return_value
        agent = Agent()
        
        # Test _tool_search_documents
        mock_idx.return_value.search.return_value = [{"score": 0.9, "content": "found", "path": "p", "filename": "f"}]
        res = agent._tool_search_documents("query")
        assert "found" in res
        
        # Test _tool_read_file
        dummy_file = tmp_path / "test.txt"
        dummy_file.write_text("file content")

        mock_pf.return_value.parse.return_value = "file content"
        res = agent._tool_read_file(str(dummy_file))
        assert "file content" in res
        
        # Test _tool_get_student_info
        mock_conn = mock_store._get_connection.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchone.return_value = (1, "Doe", "doe@example.com", "Topic", "Status", 1, "/path")

        res = agent._tool_get_student_info("Doe")
        assert "Doe" in res
        assert "doe@example.com" in res

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
    return cfg

def test_agent_init(mock_cfg):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),           patch("mcp_university.agent.engine.MetadataStore"),           patch("mcp_university.agent.engine.SearchIndex"),           patch("mcp_university.agent.engine.LLMClientWrapper"),           patch("mcp_university.agent.engine.ParserFactory"):
        
        agent = Agent()
        assert agent.model == "m"
        assert "search_documents" in agent.available_tools

def test_agent_chat(mock_cfg):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),           patch("mcp_university.agent.engine.MetadataStore"),           patch("mcp_university.agent.engine.SearchIndex"),           patch("mcp_university.agent.engine.LLMClientWrapper") as mock_llm,           patch("mcp_university.agent.engine.ParserFactory"):
        
        agent = Agent()
        mock_llm_inst = mock_llm.return_value
        mock_llm_inst.chat.return_value = {"message": {"content": "Response content"}}
        
        res = agent.chat([{"role": "user", "content": "Hello"}])
        assert "Response content" in res

def test_agent_tools(mock_cfg):
    with patch("mcp_university.agent.engine.get_config", return_value=mock_cfg),           patch("mcp_university.agent.engine.MetadataStore") as mock_store,           patch("mcp_university.agent.engine.SearchIndex") as mock_idx,           patch("mcp_university.agent.engine.LLMClientWrapper"),           patch("mcp_university.agent.engine.ParserFactory") as mock_pf:
        
        agent = Agent()
        
        # Test _tool_search_documents
        mock_idx.return_value.search.return_value = [{"score": 0.9, "content": "found", "path": "p", "filename": "f"}]
        res = agent._tool_search_documents("query")
        assert "found" in res
        
        # Test _tool_read_file
        mock_pf.return_value.parse.return_value = "file content"
        with patch("mcp_university.agent.engine.Path") as mock_path_cls:
            mock_path_cls.return_value.exists.return_value = True
            res = agent._tool_read_file("some/path")
            assert "file content" in res
        
        # Test _tool_get_student_info
        mock_store.return_value.get_node_by_property.return_value = {"id": 1, "name": "Doe", "type": "Person"}
        mock_store.return_value.get_outgoing_edges.return_value = []
        res = agent._tool_get_student_info("Doe")
        assert "Doe" in res

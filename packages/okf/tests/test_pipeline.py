import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from okf.config import OKFConfig
from okf.pipeline import run_okf_pipeline

@patch("okf.pipeline.parse_pdfs_with_liteparse")
@patch("okf.pipeline.extract_knowledge")
def test_run_okf_pipeline(mock_extract_knowledge, mock_parse_pdfs):
    with tempfile.TemporaryDirectory() as tmpdir:
        okf_dir = Path(tmpdir) / "okf"
        pdf_dir = Path(tmpdir) / "Memory"
        spec_file = Path(tmpdir) / "SPEC.md"

        okf_dir.mkdir()
        pdf_dir.mkdir()
        spec_file.write_text("OKF Spec Content", encoding="utf-8")

        # Create documents folder and a dummy source document with Reference frontmatter (Fix #1 alignment)
        doc_dir = okf_dir / "documents"
        doc_dir.mkdir(parents=True)
        (doc_dir / "regulation.md").write_text("---\ntype: Reference\ntitle: Regulation Markdown\n---\n# Regulation Markdown", encoding="utf-8")

        # Mock extracted knowledge
        mock_extract_knowledge.return_value = {
            "concepts": [
                {"name": "Concept A", "description": "Desc A", "related_concepts": []}
            ],
            "entities": [
                {"name": "Entity B", "type": "Org", "description": "Desc B"}
            ],
            "definitions": [
                {"term": "Term C", "definition": "Def C", "context": "Context C"}
            ],
            "tables": [
                {"title": "Table D", "description": "Desc D", "columns": ["Col1"], "rows": [["Val1"]]}
            ],
            "relations": []
        }

        config = OKFConfig(
            okf_dir=okf_dir,
            pdf_dir=pdf_dir,
            spec_file=spec_file,
            secrets_file=Path(tmpdir) / "secrets.env"
        )

        # Mock config's LLMClient to avoid external connections
        config._client = MagicMock()

        # Run pipeline
        run_okf_pipeline(config)

        # Check that parse_pdfs_with_liteparse was called
        mock_parse_pdfs.assert_called_once_with(pdf_dir, doc_dir)

        # Check that extract_knowledge was called
        mock_extract_knowledge.assert_called_once()

        # Check that outputs are written
        assert (okf_dir / "concepts" / "concept-a.md").exists()
        assert (okf_dir / "entities" / "entity-b.md").exists()
        assert (okf_dir / "definitions" / "term-c.md").exists()
        assert (okf_dir / "tables" / "table-d.md").exists()
        assert (okf_dir / "index.md").exists()

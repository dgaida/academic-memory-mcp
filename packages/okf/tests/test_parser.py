import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from okf.parser import parse_pdfs_with_liteparse

def test_parse_pdfs_with_liteparse_no_pdfs():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_root = Path(tmpdir) / "pdfs"
        doc_dir = Path(tmpdir) / "docs"
        pdf_root.mkdir()

        parse_pdfs_with_liteparse(pdf_root, doc_dir)
        # It should create the directory, but it should be empty since no PDFs are found
        assert doc_dir.exists()
        assert len(list(doc_dir.iterdir())) == 0

@patch("subprocess.run")
def test_parse_pdfs_with_liteparse_with_pdfs(mock_run):
    import frontmatter
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_root = Path(tmpdir) / "pdfs"
        doc_dir = Path(tmpdir) / "docs"

        pdf_root.mkdir()
        # Create subfolders to check structure preservation
        subfolder = pdf_root / "regulations"
        subfolder.mkdir()

        # Create a dummy PDF
        pdf_file = subfolder / "exam.pdf"
        pdf_file.write_bytes(b"dummy pdf content")

        # Mock subprocess to write a fake md file representing lit parse output
        def side_effect(args, **kwargs):
            out_file = Path(args[6])
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text("# Exam regulations\nSome content.", encoding="utf-8")

        mock_run.side_effect = side_effect

        parse_pdfs_with_liteparse(pdf_root, doc_dir)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "lit"
        assert args[1] == "parse"
        assert args[2] == str(pdf_file)
        assert args[4] == "markdown"

        expected_md = doc_dir / "regulations" / "exam.md"
        assert expected_md.exists()

        # Verify frontmatter has been added
        post = frontmatter.load(expected_md)
        assert post.metadata["type"] == "Reference"
        assert post.metadata["title"] == "Exam regulations"
        assert "Some content." in post.content

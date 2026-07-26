import subprocess
from pathlib import Path

def parse_pdfs_with_liteparse(pdf_root: Path, document_dir: Path) -> None:
    """Recursively parse all PDFs with LiteParse and store Markdown files in the OKF documents directory.

    Args:
        pdf_root: Root directory containing PDFs.
        document_dir: OKF documents directory.
    """
    document_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list(pdf_root.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {pdf_root}")
        return

    for pdf_file in pdf_files:
        # preserve folder structure
        relative_path = pdf_file.relative_to(pdf_root)
        md_file = (document_dir / relative_path).with_suffix(".md")

        # Skip existing Markdown files
        if md_file.exists():
            print(f"Skipping existing: {md_file}")
            continue

        md_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"Parsing: {pdf_file}")

        try:
            subprocess.run(
                [
                    "lit",
                    "parse",
                    str(pdf_file),
                    "--format",
                    "markdown",
                    "-o",
                    str(md_file)
                ],
                check=True
            )
            import frontmatter
            if md_file.exists():
                content = md_file.read_text(encoding="utf-8")
                title = None
                for line in content.splitlines():
                    line_stripped = line.strip()
                    if line_stripped.startswith("#"):
                        title = line_stripped.lstrip("#").strip()
                        break
                if not title:
                    title = md_file.stem

                metadata = {
                    "type": "Reference",
                    "title": title
                }
                post = frontmatter.Post(content, **metadata)
                md_file.write_text(frontmatter.dumps(post), encoding="utf-8")
            print(f"Created: {md_file}")
        except subprocess.CalledProcessError as e:
            print(f"ERROR parsing {pdf_file}: {e}")

from pathlib import Path
from typing import Optional
import logging
import json
import bs4

logger = logging.getLogger(__name__)

class TextParser:
    def parse(self, file_path: Path) -> Optional[str]:
        suffix = file_path.suffix.lower()
        try:
            if suffix in [".txt", ".md", ".py"]:
                return file_path.read_text(encoding="utf-8")
            elif suffix == ".json":
                data = json.loads(file_path.read_text(encoding="utf-8"))
                return json.dumps(data, indent=2)
            elif suffix == ".html":
                soup = bs4.BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
                return soup.get_text()
            elif suffix == ".ipynb":
                data = json.loads(file_path.read_text(encoding="utf-8"))
                content = []
                for cell in data.get("cells", []):
                    if cell.get("cell_type") == "markdown":
                        content.append("".join(cell.get("source", [])))
                    elif cell.get("cell_type") == "code":
                        content.append("```python\n" + "".join(cell.get("source", [])) + "\n```")
                return "\n\n".join(content)
            return None
        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {e}")
            return None

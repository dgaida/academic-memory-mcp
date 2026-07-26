import os
from pathlib import Path
from dotenv import load_dotenv
from llm_client import LLMClient

# Configurable directories
DEFAULT_OKF_DIR = Path("./okf")
DEFAULT_PDF_DIR = DEFAULT_OKF_DIR / ".." / "Memory"
DEFAULT_SPEC_FILE = Path("config/SPEC.md")
DEFAULT_SECRETS_FILE = Path("config/secrets.env")

class OKFConfig:
    """Configuration class for the OKF package."""

    def __init__(
        self,
        okf_dir: Path | str | None = None,
        pdf_dir: Path | str | None = None,
        spec_file: Path | str | None = None,
        secrets_file: Path | str | None = None,
        api_choice: str = "kiconnect",
        llm: str = "openai-gpt-oss-120b"
    ):
        """Initialize configuration, defaulting to environment variables or standard paths."""
        self.okf_dir = Path(okf_dir or os.getenv("OKF_DIR", DEFAULT_OKF_DIR)).resolve()
        self.pdf_dir = Path(pdf_dir or os.getenv("PDF_DIR", DEFAULT_PDF_DIR)).resolve()
        self.spec_file = Path(spec_file or os.getenv("OKF_SPEC_FILE", DEFAULT_SPEC_FILE)).resolve()
        self.secrets_file = Path(secrets_file or os.getenv("OKF_SECRETS_FILE", DEFAULT_SECRETS_FILE)).resolve()

        self.document_dir = self.okf_dir / "documents"
        self.concept_dir = self.okf_dir / "concepts"
        self.entity_dir = self.okf_dir / "entities"
        self.definition_dir = self.okf_dir / "definitions"
        self.table_dir = self.okf_dir / "tables"

        # Load environment secrets
        if self.secrets_file.exists():
            load_dotenv(self.secrets_file)
        else:
            load_dotenv()

        # LLM Client setup
        self.api_choice = api_choice
        self.llm = llm
        self._client = None

    @property
    def client(self) -> LLMClient:
        """Get or initialize the LLM Client."""
        if self._client is None:
            self._client = LLMClient(api_choice=self.api_choice, llm=self.llm)
        return self._client

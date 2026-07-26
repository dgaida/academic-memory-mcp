import os
from pathlib import Path
from okf.config import OKFConfig
from okf.pipeline import run_okf_pipeline

def main():
    # Use environment variables or local fallback to ensure it runs correctly anywhere.
    # We will fallback to "D:/TH_Koeln/PAV/okf" if no other directory is specified to remain backward-compatible,
    # but we will default to "./okf" in the config class or allow overriding it.
    okf_dir = os.getenv("OKF_DIR")
    if not okf_dir:
        # Check if we are running in the original path or locally
        if Path("D:/TH_Koeln/PAV/okf").exists():
            okf_dir = "D:/TH_Koeln/PAV/okf"
        else:
            okf_dir = "./okf"

    pdf_dir = os.getenv("PDF_DIR")
    if not pdf_dir:
        pdf_dir = str(Path(okf_dir) / ".." / "Memory")

    config = OKFConfig(
        okf_dir=okf_dir,
        pdf_dir=pdf_dir,
        spec_file="config/SPEC.md",
        secrets_file="config/secrets.env"
    )

    print(f"Running OKF generation pipeline...")
    print(f"OKF directory: {config.okf_dir}")
    print(f"PDF directory: {config.pdf_dir}")

    run_okf_pipeline(config)
    print("OKF Generation Pipeline completed successfully.")

if __name__ == "__main__":
    main()

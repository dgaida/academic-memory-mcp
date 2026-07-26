from okf.config import OKFConfig
from okf.parser import parse_pdfs_with_liteparse
from okf.extractor import load_spec, extract_knowledge
from okf.writer import (
    write_concept,
    write_entity,
    write_definition,
    write_table,
    create_index
)

def run_okf_pipeline(config: OKFConfig) -> None:
    """Run the complete OKF pipeline.

    Args:
        config: OKFConfig instance.
    """
    config.concept_dir.mkdir(parents=True, exist_ok=True)
    config.entity_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse PDFs
    parse_pdfs_with_liteparse(config.pdf_dir, config.document_dir)

    # Step 2: Load Specification
    spec = load_spec(config.spec_file)

    # Step 3: Extract & Write
    generated_by = f"okf-extractor/{config.llm}" if config.llm else None

    if config.document_dir.exists():
        for md_file in config.document_dir.rglob("*.md"):
            print("Processing:", md_file.name)
            markdown = md_file.read_text(encoding="utf-8")

            try:
                knowledge = extract_knowledge(markdown, md_file.name, spec, config)

                for concept in knowledge.get("concepts", []):
                    write_concept(concept, md_file.name, config.concept_dir, generated_by=generated_by, config=config)

                for entity in knowledge.get("entities", []):
                    write_entity(entity, md_file.name, config.entity_dir, generated_by=generated_by, config=config)

                for definition in knowledge.get("definitions", []):
                    write_definition(definition, md_file.name, config.definition_dir, generated_by=generated_by, config=config)

                for table in knowledge.get("tables", []):
                    write_table(table, md_file.name, config.table_dir, generated_by=generated_by, config=config)

            except Exception as e:
                print(f"ERROR processing knowledge from {md_file.name}: {e}")

    # Step 4: Create index
    create_index(
        config.okf_dir,
        config.document_dir,
        config.concept_dir,
        config.entity_dir,
        config.definition_dir,
        config.table_dir
    )

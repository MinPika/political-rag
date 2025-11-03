# pdf_pipeline.py

from sqlalchemy import select
from config.db_config import get_db
from database.models import Source, PDFExtraction
from scrapers.pdf_scraper import SimplePDFExtractor
from loguru import logger
import os


def fetch_pdf_sources(db):
    """Fetch all sources that are PDFs."""
    stmt = select(
        Source.id,
        Source.source_url,
        Source.title,
        Source.domain,
        Source.source_type,
        Source.language,
        Source.geo,
    ).where(Source.source_url.ilike("%.pdf"))
    return db.execute(stmt).all()


def extract_text_from_pdf(extractor: SimplePDFExtractor, pdf_url: str) -> str:
    """
    Download and extract text using SimplePDFExtractor.
    Returns the extracted text content as a string.
    """
    try:
        # Temporarily extract one file and get its output path
        pdf_filename = pdf_url.split("/")[-1].replace(".pdf", "")
        output_path = extractor.output_dir / f"temp_{pdf_filename}.txt"

        # Run internal process manually (not the bulk method)
        extractor.extract_single_pdf(pdf_url, 1)

        # Find the corresponding output file (the last generated .txt)
        files = sorted(
            extractor.output_dir.glob("*.txt"), key=os.path.getmtime, reverse=True
        )
        if not files:
            return ""

        latest_file = files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Clean up temporary .txt if needed
        try:
            os.remove(latest_file)
        except:
            pass

        return content

    except Exception as e:
        logger.error(f"Extraction failed for {pdf_url}: {e}")
        return ""


def process_pdfs():
    """Main pipeline for PDF extraction and database storage."""
    extractor = SimplePDFExtractor(output_dir="pdf_extracts")

    with next(get_db()) as db:
        pdf_sources = fetch_pdf_sources(db)
        logger.info(f"Found {len(pdf_sources)} PDF sources in database.")

        for (
            source_id,
            source_url,
            title,
            domain,
            source_type,
            language,
            geo,
        ) in pdf_sources:

            logger.info(f"Processing {source_url}")

            # Step 1: Extract text
            extracted_text = extract_text_from_pdf(extractor, source_url)

            if not extracted_text.strip():
                logger.warning(f"No text extracted from {source_url}")
                continue

            # Step 2: Store result
            try:
                record = PDFExtraction(
                    source_id=source_id,
                    source_url=source_url,
                    title=title,
                    domain=domain,
                    source_type=source_type,
                    language=language,
                    geo=geo,
                    extracted_text=extracted_text,
                )
                db.add(record)
                db.commit()
                logger.success(f"✅ Stored extraction for {source_url}")

            except Exception as e:
                db.rollback()
                logger.error(f"DB insert failed for {source_url}: {e}")

    extractor.cleanup()
    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    process_pdfs()

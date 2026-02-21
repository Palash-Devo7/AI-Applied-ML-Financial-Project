"""Unit tests for MetadataExtractor."""
import pytest

from app.core.metadata_extractor import MetadataExtractor


@pytest.fixture
def extractor():
    return MetadataExtractor()


def test_extract_known_ticker(extractor):
    text = "AAPL reported record revenue for fiscal year 2023."
    meta = extractor.extract_document_metadata(text, "aapl_10k.pdf")
    assert meta.ticker == "AAPL"
    assert meta.company == "Apple"


def test_extract_year(extractor):
    text = "For the fiscal year ended September 30, 2023, total net revenues..."
    meta = extractor.extract_document_metadata(text, "report.pdf")
    assert meta.year == 2023


def test_extract_report_type_10k(extractor):
    text = "Annual Report on Form 10-K for the fiscal year ended..."
    meta = extractor.extract_document_metadata(text, "apple_10k_2023.pdf")
    assert meta.report_type == "10-K"


def test_extract_report_type_10q(extractor):
    text = "Quarterly Report on Form 10-Q for the quarter ended..."
    meta = extractor.extract_document_metadata(text, "report.pdf")
    assert meta.report_type == "10-Q"


def test_extract_quarter(extractor):
    text = "Q3 results showed strong performance across all segments."
    meta = extractor.extract_document_metadata(text, "report.pdf")
    assert meta.quarter == "Q3"


def test_extract_sector_technology(extractor):
    text = "The company operates in the technology sector, providing software solutions."
    meta = extractor.extract_document_metadata(text, "report.pdf")
    assert meta.sector == "Technology"


def test_overrides_take_precedence(extractor):
    text = "AAPL 10-K 2023 report."
    meta = extractor.extract_document_metadata(
        text, "report.pdf", overrides={"company": "Override Corp", "year": 2022}
    )
    assert meta.company == "Override Corp"
    assert meta.year == 2022


def test_filename_year_fallback(extractor):
    meta = extractor.extract_document_metadata("", "report_2021.pdf")
    assert meta.year == 2021


def test_section_type_risk(extractor):
    text = "RISK FACTORS\nThe company faces significant competitive pressures."
    section_type = extractor.extract_section_type(text)
    assert section_type == "RISK_FACTORS"


def test_section_type_revenue(extractor):
    text = "RESULTS OF OPERATIONS\nTotal revenues increased 15% year-over-year."
    section_type = extractor.extract_section_type(text)
    assert section_type == "RESULTS_OF_OPERATIONS"


def test_section_type_general_fallback(extractor):
    text = "Some unrecognized section header here."
    section_type = extractor.extract_section_type(text)
    assert section_type == "GENERAL"

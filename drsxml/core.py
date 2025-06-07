import pandas as pd
from lxml import etree
from datetime import datetime
from pathlib import Path

from .config import (
    DATA_DIR,
    OUTPUT_DIR,
    NS,
    XSD_VERSION,
    SCHEMA_LOCATION,
    DEPOSITOR_NAME,
    DEPOSITOR_EMAIL,
    REGISTRANT,
)


def preview_xml_tree(doi_batch):
    # Pretty-print the XML
    xml_string = etree.tostring(
        doi_batch, pretty_print=True, xml_declaration=True, encoding="utf-8"
    ).decode("utf-8")

    # Print the formatted XML
    print(xml_string)


def extract_date_parts(date_str: str) -> dict:
    """
    Split a date string into year, month, day components.
    """
    dt = datetime.fromisoformat(date_str)
    return {"year": dt.year, "month": dt.month, "day": dt.day}


def validate(tree: etree._ElementTree, xsd_path: Path) -> None:
    """
    Validate XML tree against the given XSD schema.
    """
    xmlschema = etree.XMLSchema(etree.parse(str(xsd_path)))
    xmlschema.assertValid(tree)


def load_xls_data(fname: str, sheet_name: str = None) -> list[dict]:
    path = DATA_DIR / fname
    df = pd.read_excel(path, sheet_name=sheet_name or 0, engine="xlrd")

    if "publication_date" not in df.columns:
        raise ValueError("`publication_date` column is required")

    df["publication_date"] = pd.to_datetime(df["publication_date"], errors="raise")
    df["year"] = df["publication_date"].dt.year
    df["month"] = df["publication_date"].dt.month
    df["day"] = df["publication_date"].dt.day

    df = df.fillna("").astype(str)

    return df.to_dict(orient="records")


def write_xml_to_file(tree: etree._ElementTree, filename: str) -> None:
    output_path = OUTPUT_DIR / filename
    xml_bytes = etree.tostring(
        tree, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    output_path.write_bytes(xml_bytes)
    print(f"XML written to {output_path}")


def generate_doi_batch_root() -> tuple[etree.Element, etree.Element, etree.Element]:
    """
    Create the <doi_batch> root element with namespaces, version, schemaLocation.
    Returns (root, head, body).
    """
    root = etree.Element("doi_batch", nsmap=NS)
    root.set("version", XSD_VERSION)
    root.set(
        "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", SCHEMA_LOCATION
    )
    head = etree.SubElement(root, "head")
    body = etree.SubElement(root, "body")
    return root, head, body


def populate_doi_batch_head(head: etree.Element, fname: str) -> None:
    """
    Populate the <head> element with batch metadata (doi_batch_id, timestamp, depositor, registrant).
    """
    batch_id_base = Path(fname).stem
    date_str = datetime.now().strftime("%y%m%d")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S") + "0000"

    etree.SubElement(head, "doi_batch_id").text = f"{batch_id_base}-{date_str}"
    etree.SubElement(head, "timestamp").text = timestamp

    depositor = etree.SubElement(head, "depositor")
    etree.SubElement(depositor, "depositor_name").text = DEPOSITOR_NAME
    etree.SubElement(depositor, "email_address").text = DEPOSITOR_EMAIL

    etree.SubElement(head, "registrant").text = REGISTRANT


# Placeholder for content-specific body population functions,
# to be implemented elsewhere or here later


def populate_book_review_body(
    body: etree.Element, records: list[dict], verbose: bool = False
) -> None:
    """
    Populate the <body> element with book review records.
    """
    for idx, record in enumerate(records):
        if verbose:
            print(f"Processing record {idx}: {record.get('title', '')}")

        report_paper = etree.SubElement(body, "report-paper")
        report_paper_metadata = etree.SubElement(
            report_paper, "report-paper_metadata", language="en"
        )

        # Contributors
        contributor = etree.SubElement(report_paper_metadata, "contributors")
        person_name = etree.SubElement(
            contributor, "person_name", sequence="first", contributor_role="author"
        )
        etree.SubElement(person_name, "given_name").text = record.get(
            "author1_fname", ""
        )
        etree.SubElement(person_name, "surname").text = record.get("author1_lname", "")

        # Affiliations
        affiliations = etree.SubElement(person_name, "affiliations")
        institution = etree.SubElement(affiliations, "institution")
        institution_name_text = (
            record.get("author1_institution", "").strip() or "Design Research Society"
        )
        etree.SubElement(institution, "institution_name").text = institution_name_text

        # Titles
        titles = etree.SubElement(report_paper_metadata, "titles")
        etree.SubElement(titles, "title").text = record.get("title", "")

        # Edition number
        etree.SubElement(report_paper_metadata, "edition_number").text = "0"

        # Publication date
        publication_date = etree.SubElement(report_paper_metadata, "publication_date")
        date_str = record.get("publication_date", "").split(" ")[0]  # e.g. "2023-06-05"
        if date_str:
            try:
                year_data, month_data, day_data = date_str.split("-")
                etree.SubElement(publication_date, "month").text = month_data
                etree.SubElement(publication_date, "day").text = day_data
                etree.SubElement(publication_date, "year").text = year_data
            except ValueError:
                # Handle malformed dates gracefully
                pass

        # DOI data
        doi_data = etree.SubElement(report_paper_metadata, "doi_data")
        doi_text = record.get("doi", "").replace("doi.org/", "")
        etree.SubElement(doi_data, "doi").text = doi_text
        etree.SubElement(doi_data, "resource").text = record.get("calc_url", "")


def populate_proceedings_body(
    body: etree.Element, records: list[dict], issn: str = None, verbose: bool = False
) -> None:
    """
    Populate the <body> element with proceedings records.
    Creates the <conference> element and populates metadata and papers.
    If ISSN is provided, treat as a proceedings series, otherwise as single proceedings.
    """
    if verbose:
        print("Creating <conference> element in <body>")

    conference = etree.SubElement(body, "conference")

    if verbose:
        print("Populating <event_metadata>")
    # Populate event metadata (hard-coded + record info)
    populate_event_metadata(conference, records, verbose=verbose)

    if verbose:
        print("Populating proceedings metadata")
    # Populate proceedings or series metadata based on ISSN presence
    populate_proceedings_metadata(conference, records, issn=issn, verbose=verbose)

    if verbose:
        print(f"Populating {len(records)} conference papers")
    # Populate conference papers
    populate_conference_papers(conference, records, verbose=verbose)


def populate_event_metadata(conference: etree.Element, records: list[dict]) -> None:
    event_metadata = etree.SubElement(conference, "event_metadata")

    # Example static info (replace with your actual hard-coded data)
    etree.SubElement(event_metadata, "conference_name").text = "My Conference Name"
    etree.SubElement(event_metadata, "conference_acronym").text = "MCN"
    etree.SubElement(event_metadata, "conference_date").text = "2025-06-10"

    # Possibly extract location or year info from first record if needed


def populate_proceedings_metadata(
    conference: etree.Element,
    records: list[dict],
    issn: str = None,
) -> None:

    if issn is None:
        proceedings_metadata = etree.SubElement(conference, "proceedings_metadata")
        # Add shared metadata elements here
        # e.g. title, ISBN, publication_date, publisher
    else:
        series_metadata = etree.SubElement(conference, "proceedings_series_metadata")
        # Add shared metadata elements
        # Plus ISSN and series-specific elements


def populate_conference_papers(
    conference: etree.Element, records: list[dict], verbose: bool = False
) -> None:

    for idx, record in enumerate(records):
        if verbose:
            print(f"Processing paper {idx}: {record.get('title', '')}")

        paper = etree.SubElement(conference, "conference_paper")
        # Populate paper metadata elements (authors, title, pages, doi, etc.)

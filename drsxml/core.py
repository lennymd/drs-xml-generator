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

    df = df.fillna("").astype(str)

    if "publication_date" in df.columns:
        df["publication_date"] = pd.to_datetime(df["publication_date"], errors="raise")
        df["year"] = df["publication_date"].dt.year
        df["month"] = df["publication_date"].dt.month
        df["day"] = df["publication_date"].dt.day
        return df.to_dict(orient="records")

    if all(col in df.columns for col in ["start_date", "end_date", "conference_dates"]):
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")

        df["start_day"] = df["start_date"].dt.day.astype(str).str.zfill(2)
        df["end_day"] = df["end_date"].dt.day.astype(str).str.zfill(2)
        df["start_month"] = df["start_date"].dt.month.astype(str).str.zfill(2)
        df["end_month"] = df["end_date"].dt.month.astype(str).str.zfill(2)
        df["start_year"] = df["start_date"].dt.year.astype(str)
        df["end_year"] = df["end_date"].dt.year.astype(str)
        return df.to_dict(orient="records")

    raise ValueError("Unknown XLS file format: missing expected columns")


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


def populate_book_review_body(
    body: etree.Element, records: list[dict], verbose: bool = False
) -> None:
    for idx, record in enumerate(records):
        if verbose:
            print(f"Processing record {idx}: {record.get('title', '')}")

        report_paper = etree.SubElement(body, "report-paper")
        report_paper_metadata = etree.SubElement(
            report_paper, "report-paper_metadata", language="en"
        )

        # Use add_contributors instead of manual single author block
        add_contributors(report_paper_metadata, record)

        # Titles
        titles = etree.SubElement(report_paper_metadata, "titles")
        etree.SubElement(titles, "title").text = record.get("title", "")

        # Edition number
        etree.SubElement(report_paper_metadata, "edition_number").text = "0"

        # Publication date
        publication_date = etree.SubElement(report_paper_metadata, "publication_date")
        our_date = record.get("publication_date", "")
        date_str = str(our_date).strip().split(" ")[0]  # e.g. "2023-06-05"

        year_data, month_data, day_data = date_str.split("-")
        etree.SubElement(publication_date, "year").text = year_data
        etree.SubElement(publication_date, "month").text = month_data
        etree.SubElement(publication_date, "day").text = day_data

        # DOI data
        add_doi_data(
            report_paper_metadata, record.get("doi", ""), record.get("calc_url", "")
        )


def populate_proceedings_body(
    body: etree.Element, records: list[dict], conf_info: dict
) -> None:
    conference = etree.SubElement(body, "conference")
    populate_event_metadata(conference, conf_info, records)
    populate_proceedings_metadata(conference, conf_info, records)
    populate_conference_papers(conference, conf_info, records)


def populate_event_metadata(
    conference: etree.Element,
    conf_info: dict,
    records: list[dict],
) -> None:
    event_metadata = etree.SubElement(conference, "event_metadata")
    etree.SubElement(event_metadata, "conference_name").text = conf_info.get("name", "")
    etree.SubElement(event_metadata, "conference_acronym").text = conf_info.get(
        "acronym", ""
    )

    first_record = records[0]  # Assume all share the same conference date info

    conference_date = etree.SubElement(
        event_metadata,
        "conference_date",
        start_day=first_record.get("start_day", "").zfill(2),
        end_day=first_record.get("end_day", "").zfill(2),
        start_month=first_record.get("start_month", "").zfill(2),
        end_month=first_record.get("end_month", "").zfill(2),
        start_year=first_record.get("start_year", ""),
        end_year=first_record.get("end_year", ""),
    )

    conference_date.text = first_record.get("conference_dates", "")


def add_series_metadata(temp_root: etree.Element, conf_info: dict) -> None:
    series_metadata = etree.SubElement(temp_root, "series_metadata")
    titles_series = etree.SubElement(series_metadata, "titles")
    title_series = etree.SubElement(titles_series, "title")
    title_series.text = conf_info.get("series_title", "")

    issn_text = conf_info.get("issn", "")
    if issn_text:
        etree.SubElement(series_metadata, "issn").text = issn_text


def add_doi_data(parent: etree.Element, doi: str, resource: str) -> None:
    doi_data = etree.SubElement(parent, "doi_data")
    etree.SubElement(doi_data, "doi").text = doi
    etree.SubElement(doi_data, "resource").text = resource


def populate_proceedings_metadata(
    conference: etree.Element,
    conf_info: dict,
    records: list[dict],
) -> None:

    issn = conf_info.get("issn")

    if issn in (None, ""):
        temp_root = etree.SubElement(conference, "proceedings_metadata", language="en")
    else:
        temp_root = etree.SubElement(conference, "proceedings_series_metadata")
        add_series_metadata(temp_root, conf_info)

    # proceedings_title
    proceedings_title = conf_info.get("proceedings_title", "")
    if not proceedings_title:
        proceedings_title = conf_info.get("name", "")
    etree.SubElement(temp_root, "proceedings_title").text = proceedings_title

    # publisher
    publisher = etree.SubElement(temp_root, "publisher")
    etree.SubElement(publisher, "publisher_name").text = "Design Research Society"

    # publication_date
    publication_date = etree.SubElement(
        temp_root, "publication_date", media_type="online"
    )

    first_record = records[0]
    etree.SubElement(publication_date, "month").text = first_record.get(
        "start_month", ""
    )
    etree.SubElement(publication_date, "day").text = first_record.get("start_day", "")
    etree.SubElement(publication_date, "year").text = first_record.get("start_year", "")
    # isbn or noisbn
    isbn = conf_info.get("isbn", "")
    if isbn:
        etree.SubElement(temp_root, "isbn").text = isbn
    else:
        noisbn = etree.SubElement(temp_root, "noisbn")
        noisbn.set("reason", "simple_series")

    # DOI data
    add_doi_data(
        temp_root,
        conf_info.get("volume_doi", ""),
        conf_info.get("volume_url", ""),
    )


def populate_conference_papers(
    conference: etree.Element,
    conf_info: dict,
    records: list[dict],
) -> None:

    for idx, record in enumerate(records):

        paper = etree.SubElement(
            conference,
            "conference_paper",
            language="en",
            publication_type="full_text",
        )

        # Contributors placeholder
        add_contributors(paper, record)

        # Title
        titles = etree.SubElement(paper, "titles")
        etree.SubElement(titles, "title").text = record.get("title", "")

        # Publication date
        publication_date = etree.SubElement(paper, "publication_date")
        publication_date.set("media_type", "online")
        etree.SubElement(publication_date, "month").text = record.get("start_month", "")
        etree.SubElement(publication_date, "day").text = record.get("start_day", "")
        etree.SubElement(publication_date, "year").text = record.get("start_year", "")

        # DOI data (using your add_doi_data helper)
        add_doi_data(paper, record.get("doi", ""), record.get("calc_url", ""))


def add_contributors(parent: etree.Element, record: dict) -> None:
    """
    Add contributors from the record to the given parent XML element.

    - The first author has sequence="first"
    - Additional authors have sequence="additional"
    - For every author, add affiliation only if the institution name exists and is non-empty.
    """

    contributors = etree.SubElement(parent, "contributors")

    index = 1
    while True:
        fname_key = f"author{index}_fname"
        lname_key = f"author{index}_lname"
        inst_key = f"author{index}_institution"

        lname = record.get(lname_key, "").strip()
        fname = record.get(fname_key, "").strip()
        if not lname:
            break  # No more authors, exit loop

        # Set sequence attribute: first author vs additional authors
        sequence = "first" if index == 1 else "additional"

        person_name = etree.SubElement(
            contributors,
            "person_name",
            sequence=sequence,
            contributor_role="author",
        )

        if fname:
            etree.SubElement(person_name, "given_name").text = fname

        etree.SubElement(person_name, "surname").text = lname

        # Add affiliation only if institution_name exists and is non-empty
        institution_name = record.get(inst_key, "").strip()
        if institution_name:
            affiliations = etree.SubElement(person_name, "affiliations")
            institution = etree.SubElement(affiliations, "institution")
            etree.SubElement(institution, "institution_name").text = institution_name

        index += 1

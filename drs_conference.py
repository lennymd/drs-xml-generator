from drsxml.core import (
    generate_doi_batch_root,
    populate_doi_batch_head,
    preview_xml_tree,
    load_xls_data,
    write_xml_to_file,
    populate_proceedings_body,
)

# Define the conference information
conf_info = {
    "data_file": "drsf25.xls",
    "name": "Designing Retail & Services Futures Colloquium 2025: Sustainable Retail and Services Futures",
    "acronym": "DRSF 2025",
    "volume_doi": "10.21606/drsf.102",
    "volume_url": "https://dl.designresearchsociety.org/conference-volumes/68/",
    "issn": "",
    "isbn": "9781912294664",
    "series_title": "",
}

OUT_FILE = "250929-drsf2025.xml"

# Load the data from the XLS file
records = load_xls_data(conf_info.get("data_file"))


# GENERATE XML TREE

# Create the root element for the DOI batch
root, head, body = generate_doi_batch_root()

# Populate the head with metadata
populate_doi_batch_head(head, conf_info.get("data_file"))

body.clear()

# Populate the body with book review records
populate_proceedings_body(body, records, conf_info)

write_xml_to_file(root, OUT_FILE)

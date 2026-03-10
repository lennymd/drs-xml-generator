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
    "data_file": "lxd25.xls",
    "name": "LearnXDesign 2025",
    "acronym": "LearnXDesign 2025",
    "volume_doi": "10.21606/drslxd.2025.cv",
    "volume_url": "https://dl.designresearchsociety.org/learnxdesign/learnxdesign2025",
    "issn": "",
    "isbn": "",
    "series_title": "",
}

OUT_FILE = "260309-lxd25.xml"

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

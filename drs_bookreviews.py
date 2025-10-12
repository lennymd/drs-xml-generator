from drsxml.core import (
    generate_doi_batch_root,
    populate_doi_batch_head,
    populate_book_review_body,
    load_xls_data,
    write_xml_to_file,
)

# LOAD XLS FILE FOR PROCESSING

FILE = "books1012.xls"

records = load_xls_data(FILE)

# PREVIEW RECORDS
# for rec in records[:5]:
#     print(rec)


# GENERATE XML TREE

# Create the root element for the DOI batch
root, head, body = generate_doi_batch_root()

# Populate the head with metadata
populate_doi_batch_head(head, FILE)

# Populate the body with book review records
populate_book_review_body(body, records)

# Save XML to file

write_xml_to_file(root, "book-reviews.xml")

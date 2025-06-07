from pathlib import Path

# Root-relative data directories
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Crossref schema version
XSD_VERSION = "5.3.0"

# Namespace map for XML generation
NS = {
    None: "http://www.crossref.org/schema/5.3.0",  # default
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "jats": "http://www.ncbi.nlm.nih.gov/JATS1",
    "fr": "http://www.crossref.org/fundref.xsd",
    "mml": "http://www.w3.org/1998/Math/MathML",
}

# xsi:schemaLocation attribute value
SCHEMA_LOCATION = (
    "http://www.crossref.org/schema/5.3.0 "
    "https://www.crossref.org/schemas/crossref5.3.0.xsd"
)

# Depositor and registrant info for <head>
DEPOSITOR_NAME = "desres:desres"
DEPOSITOR_EMAIL = "dl@designresearchsociety.org"
REGISTRANT = "Digital Library"

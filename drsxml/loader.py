import pandas as pd
from .config import DATA_DIR


def load_book_reviews(fname: str, sheet_name: str = None) -> list[dict]:
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


def load_proceedings(fname: str) -> list[dict]:
    raise NotImplementedError("load_proceedings() is not yet implemented.")

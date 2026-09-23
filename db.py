import os
import pandas as pd
import streamlit as st

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


def ejecutar_query(query, params=None):

    with engine.begin() as conn:

        return conn.execute(
            text(query),
            params or {}
        )


def obtener_dataframe(query, params=None):

    with engine.connect() as conn:

        return pd.read_sql(
            text(query),
            conn,
            params=params or {}
        )
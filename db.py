import os
import streamlit as st

from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = None

try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except:
    DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
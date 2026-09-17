import os,pandas as pd
from sqlalchemy import create_engine,text
from dotenv import load_dotenv
load_dotenv()
engine=create_engine(os.getenv("DATABASE_URL"))

def ejecutar_query(q,p=None):
    with engine.begin() as c: return c.execute(text(q),p or {})

def obtener_dataframe(q):
    with engine.connect() as c: return pd.read_sql(q,c)

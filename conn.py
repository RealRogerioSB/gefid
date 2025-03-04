import polars as pl
import sqlalchemy as sa

engine = sa.create_engine("db2+ibm_db://DB2I13E5:98680081@gwdb2.bb.com.br:50100/BDB2P04")


def conn(sql):
    return pl.read_database(query=sql, connection=engine, infer_schema_length=None)

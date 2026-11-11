import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb
    DUCKDB_FILE = "../../dbt_ETM/dev.duckdb"

    con = duckdb.connect(database=DUCKDB_FILE, read_only=True)
    return con, mo


@app.cell
def _(con, mo):
    cites_2024 = mo.sql(
        f"""
        SELECT * FROM "main_raw"."raw_cites" WHERE "year" = 2024 LIMIT 100
        """,
        engine=con
    )
    return (cites_2024,)


@app.cell
def _(cites_2024):
    cites_2024.describe()
    return


@app.cell
def _(con, mo):
    _df = mo.sql(
        f"""
        SELECT DISTINCT "source" from "main_raw"."raw_cites"
        """,
        engine=con
    )
    return


if __name__ == "__main__":
    app.run()

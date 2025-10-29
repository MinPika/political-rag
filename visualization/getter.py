from sqlalchemy import select
from config.db_config import engine
from sqlalchemy import Table, MetaData

metadata = MetaData()
sources = Table("sources", metadata, autoload_with=engine)

stmt = select(sources.c.source_url).order_by(sources.c.source_url.asc()).limit(153)

with engine.connect() as conn:
    result = conn.execute(stmt)
    source_urls = [
        row[0] for row in result
    ]  # row[0] because only one column is selected

for url in source_urls:
    print(url)

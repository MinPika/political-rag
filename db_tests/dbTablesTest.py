from sqlalchemy import inspect
from config.db_config import engine  # assuming your engine is defined there

inspector = inspect(engine)
tables = inspector.get_table_names()
print(tables)

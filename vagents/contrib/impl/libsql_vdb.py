from typing import List
from vagents.core import VectorDB, Field, Embedding

try:
    import libsql
except ImportError:
    raise ImportError(
        "libsql is not installed. Please install it using `pip install libsql`."
    )


class LibSQLVDB(VectorDB):
    def __init__(self, conn_string: str):
        super().__init__()
        self.conn_string = conn_string
        self.connection = libsql.connect(self.conn_string)

    def _map_field_type(self, field: Field):
        assert isinstance(field, Field), "Field must be an instance of Field class"

        if field.field_type == str:
            return "TEXT"
        elif field.field_type == int:
            return "INTEGER"
        elif field.field_type == float:
            return "FLOAT"
        elif field.field_type == Embedding:
            assert (
                "dimension" in field.kwargs
            ), "Embedding field must specify 'dimension'"
            return f'F32_BLOB({field.kwargs.get("dimension", 3)})'
        raise ValueError(f"Unsupported field type: {field.field_type}")

    def create_table(self, table_name, attributes: dict, **kwargs):
        columns = ", ".join(
            [f"{k} {self._map_field_type(v)}" for k, v in attributes.items()]
        )
        create_table_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
            {columns}
        );"""
        with self.connection as con:
            cur = con.cursor()
            cur.execute(create_table_sql)
            con.commit()
        return True

    def insert(self, table_name: str, data: dict):
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        data_values = ()
        for value in data.values():
            if isinstance(value, list):
                data_values += (f"[{','.join(str(x) for x in value)}]",)
            else:
                data_values += (value,)
        with self.connection as con:
            cur = con.cursor()
            cur.execute(insert_sql, data_values)
            con.commit()
        return True

    def query(self, table_name: str, field_names: List[str], **kwargs) -> List[dict]:
        sql = f"SELECT {', '.join(field_names)} FROM {table_name}"
        if kwargs:
            conditions = " AND ".join([f"{k} = ?" for k in kwargs.keys()])
            sql += f" WHERE {conditions}"
            params = tuple(kwargs.values())
        else:
            params = ()
        with self.connection as con:
            cur = con.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
        return rows

    def create_index(self, table_name: str, field_name: str):
        """
        Create an index on a specific field in the table.

        :param table_name: The name of the table to create the index on.
        :param field_name: The name of the field to index.
        """
        create_index_sql = f"CREATE INDEX IF NOT EXISTS _{field_name}_index ON {table_name} (libsql_vector_idx({field_name}));"

        with self.connection as con:
            cur = con.cursor()
            cur.execute(create_index_sql)
            con.commit()
        return True

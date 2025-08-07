import os
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
        # get dir name from conn_string
        dir_name = os.path.dirname(conn_string)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
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
            return f'F32_BLOB({field.kwargs.get("dimension", 768)})'
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
            elif hasattr(value, "tolist"):  # Handle numpy arrays
                # Convert numpy array to list first
                vector_list = value.tolist()
                data_values += (f"[{','.join(str(x) for x in vector_list)}]",)
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

    def vector_search(
        self,
        table_name: str,
        field_names: List[str],
        vector: List[float],
        top_k: int = 10,
        **kwargs,
    ) -> List:
        """
        Perform vector similarity search using libsql's vector_top_k function.

        :param table_name: The name of the table to search in.
        :param field_names: List of field names to return.
        :param vector: The query vector for similarity search.
        :param top_k: The number of top similar results to return.
        :return: A list of top_k similar results from the vector database.
        """
        # Find the embedding field for this table (we need the index name)
        from vagents.core.vdb import __ALL_TABLES__

        embedding_field_name = None
        if table_name in __ALL_TABLES__:
            for field_name, field in __ALL_TABLES__[table_name].items():
                if isinstance(field, Field) and field.field_type == Embedding:
                    embedding_field_name = field_name
                    break

        if not embedding_field_name:
            raise ValueError(f"No embedding field found for table {table_name}")

        # Format the vector as a string for libsql
        vector_str = f"[{','.join(str(x) for x in vector)}]"

        # Build the SQL query using vector_top_k
        index_name = f"_{embedding_field_name}_index"
        fields_str = ", ".join(field_names)

        sql = f"""
        SELECT {fields_str}
        FROM vector_top_k('{index_name}', '{vector_str}', {top_k})
        JOIN {table_name} ON {table_name}.rowid = id
        """

        # Add any additional WHERE conditions
        if kwargs:
            conditions = " AND ".join([f"{table_name}.{k} = ?" for k in kwargs.keys()])
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

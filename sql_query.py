from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

from dataclasses import dataclass


class CreateTableQuery:
    def __init__(self, table_name: str, if_not_exists=False, schema: str = None):
        self.table = TableSpec(table_name=table_name, schema=schema)
        self.if_not_exists = if_not_exists
        self.columns = []

    def add_column(self, name: str, _type: str, constraint: str = None):
        self.columns.append((name, _type, constraint or ''))

    def build(self):
        if not self.columns:
            raise SqlQueryError(f'no columns for table {self.table.build_full_table_name()}')

        i_n_e = "IF NOT EXISTS" if self.if_not_exists else ''
        columns = ',\n'.join(
            (q(col[0]) + ' ' + col[1] + ' ' + col[2] for col in self.columns)
        )

        result = f"""CREATE TABLE {i_n_e} {self.table.build_full_table_name()} (
        {columns}
        );
        """
        return result


class DmlWriteQuery(ABC):
    def __init__(self, table_name: str, schema: str = None):
        self.table = TableSpec(table_name=table_name, schema=schema)
        self.column_data = {}

    def add_column(self, name: str, value):
        self.column_data[name] = value

    @abstractmethod
    def build(self) -> Tuple[str, tuple]:
        ...


class DmlSearchQuery(ABC):
    def __init__(self):
        self.where: List[WhereItem] = []

    def add_where(self, column, op, value, table_alias=None):
        self.where.append(WhereItem(table_alias, column, op, (value,)))

    def add_where_expr(self, expr, *params):
        self.where.append(WhereItem(expr=expr, params=params))

    def build_where_expression(self, joiner="\nAND ") -> str:
        return joiner.join(
            (x.build() for x in self.where)
        )

    def get_where_params(self) -> list:
        result = []
        for wh in self.where:
            if wh.params is not None and isinstance(wh.params, tuple):
                result.extend(wh.params)
            else:
                raise SqlQueryError(f'Parameters of WhereItem must be tuple! : {str(wh)}')
        return result


class InsertQuery(DmlWriteQuery):
    def build(self) -> Tuple[str, tuple]:
        columns = ",\n".join((q(col) for col in self.column_data.keys()))
        result = f'''INSERT INTO {self.table.build_full_table_name()}(
            {columns}
        ) VALUES (
        {", ".join('?' for _ in self.column_data)}
        );
        '''
        values = tuple(self.column_data.values())
        return result, values


class UpdateQuery(DmlWriteQuery, DmlSearchQuery):
    def __init__(self, table_name: str, schema: str = None):
        DmlWriteQuery.__init__(self, table_name, schema=schema)
        DmlSearchQuery.__init__(self)

    def build(self) -> Tuple[str, tuple]:
        if not self.where:
            raise SqlQueryError('Update without where!')
        columns = ",\n".join(
            (q(col) + ' = ?' for col in self.column_data.keys())
        )

        result = f'''UPDATE {self.table.build_full_table_name()} SET
        {columns}
        WHERE
        {self.build_where_expression()};
        '''

        params1 = self.column_data.values()
        params2 = self.get_where_params()
        params = tuple(params1) + tuple(params2)

        return result, params


class SelectQuery(DmlSearchQuery):
    def __init__(self, table_name: str, schema: str = None):
        DmlSearchQuery.__init__(self)
        self.main_table = TableSpec(table_name, 'T1', schema)
        self.tables = [self.main_table]
        self._next_alias_num = 2
        self.select = []
        self.order_by = []
        self.limit = None
        self.offset = None

    def add_select_column(self, col: str, alias: str = None, table_alias: str = None):
        table_alias = table_alias or self.main_table.table_alias
        self.select.append(SelectColumn(table_alias, col, alias))

    def add_select_expr(self, expr: str, alias: str = None):
        self.select.append(SelectColumn(expr=expr, alias=alias))

    def add_order_by(self, col: str, reverse: bool = False, table_alias: str = None, nulls_last: Optional[bool] = None):
        """
        Add order by condition
        :param col: column name
        :param reverse: descending order
        :param table_alias: optional table alias
        :param nulls_last: specify NULLs order. Default is unspecified (=default for db)
        """
        table_alias = table_alias or self.main_table.table_alias
        self.order_by.append(OrderByItem(table_alias, col, reverse, nulls_last))

    def add_table(self, table_name: str) -> str:
        table_alias = f'T{self._next_alias_num}'
        self._next_alias_num += 1
        self.tables.append(TableSpec(table_name, table_alias))
        return table_alias

    def add_limit_offset(self, limit: int, offset: int):
        self.limit = limit
        self.offset = offset

    def build(self) -> Tuple[str, tuple]:
        where = self.build_where_expression()

        result = f"""SELECT
            {self.build_columns()}
        FROM {self.build_tables()}
        {("WHERE " + where) if where else ''}                
        """
        order = self.build_order_by()
        if order:
            result += "ORDER BY " + order + "\n"
        params = self.get_where_params()
        if isinstance(self.limit, int):
            result += "LIMIT ?\n"
            params.append(self.limit)
        if isinstance(self.offset, int):
            result += "OFFSET ?\n"
            params.append(self.offset)

        return result, tuple(params)

    def build_columns(self):
        if not self.select:
            raise SqlQueryError('No select columns!')

        return ",\n".join(
            x.build() for x in self.select
        )

    def build_order_by(self):
        return ",\n".join(
            x.build() for x in self.order_by
        )

    def build_tables(self):
        return ",\n".join(x.build_table_ref() for x in self.tables)


@dataclass
class ColumnSpec:
    table_alias: str = None
    column: str = None

    def build_column(self):
        if self.column:
            if self.table_alias:
                return f'{self.table_alias}.{q(self.column)}'
            else:
                return q(self.column)


@dataclass
class WhereItem(ColumnSpec):
    op: str = None
    params: tuple = None
    expr: str = None

    def build(self):
        if not self.expr:
            return self.build_column() + f" {self.op} ?"
        return self.expr



@dataclass
class SelectColumn(ColumnSpec):
    alias: str = None
    expr: str = None

    def build(self):
        result = self.build_column() or self.expr
        if self.alias:
            result += " AS " + self.alias
        return result


@dataclass
class OrderByItem(ColumnSpec):
    descending: bool = False
    nulls_last: Optional[bool] = None

    def build(self):
        result = self.build_column() + (" DESC" if self.descending else '')
        if isinstance(self.nulls_last, bool):
            if self.nulls_last:
                result += " NULLS LAST"
            else:
                result += "NULLS FIRST"
        return result



@dataclass
class TableSpec:
    table_name: str
    table_alias: str = None
    schema: str = None

    def build_full_table_name(self):
        if self.table_name:
            r = q(self.table_name)
            if self.schema:
                r = q(self.schema) + "." + r
            return r

    def build_table_ref(self):
        if self.table_name:
            r = self.build_full_table_name()
            if self.table_alias:
                r += " AS " + self.table_alias
            return r


class SqlQueryError(Exception): pass


def q(name: str):
    """
    quote name for use as table or column name
    :param name: name
    :return: quoted name
    """
    name = name.replace('"', '').replace("'", '')
    return f'"{name}"'

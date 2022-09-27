from typing import Literal

from lark import Lark, Transformer
from sqlalchemy import and_, func, or_

from .models import Document

GRAMMAR = r"""
%import common.ESCAPED_STRING
%import common.NUMBER
%import common.WS

%ignore WS

field: /[^\s]+/

comp_operator:   "="      -> eq
               | "!="     -> ne
               | ">"      -> gt
               | ">="     -> gte
               | "<"      -> lt
               | "<="     -> lte
               | "~="     -> regex
               | "like"   -> like
               | "is"     -> is_
               | "is_not" -> is_not

value:   "null"         -> null
       | "true"         -> true
       | "false"        -> false
       | NUMBER         -> number
       | ESCAPED_STRING -> string

rule: field comp_operator value

or_expression: expression "||" expression

and_expression: expression "&&" expression

expression: ("(" expression ")") | or_expression | and_expression | rule
"""

Operator = Literal["=", "!=", ">", ">=", "<", "<=", "~=", "like", "is", "is_not"]

Value = None | bool | float | int | str

Rule = tuple[str, Operator, Value]


class Q:
    def __init__(self, rule: Rule):
        field, op, value = rule

        field = f"$.{field}[0]"
        column = func.JSON_EXTRACT(Document.fields, field)

        match op:
            case "=":
                expression = column == value
            case "!=":
                expression = column != value
            case ">":
                expression = column > value
            case ">=":
                expression = column >= value
            case "<":
                expression = column < value
            case "<=":
                expression = column <= value
            case "~=":
                expression = column.regexp_match(value)
            case "like":
                expression = column.like(value)
            case "is":
                expression = column.is_(value)
            case "is_not":
                expression = column.is_not(value)
            case _:
                raise

        self.expression = expression

    def __and__(self, other: "Q") -> "Q":
        self.expression = and_(self.expression, other.expression)
        return self

    def __or__(self, other: "Q") -> "Q":
        self.expression = or_(self.expression, other.expression)
        return self

    def __repr__(self) -> str:
        return str(self.expression)


class QueryToQ(Transformer):
    @staticmethod
    def _const(s):
        return lambda *_: s

    null = _const(None)
    true = _const(True)
    false = _const(False)

    eq = _const("=")
    ne = _const("!=")
    gt = _const(">")
    gte = _const(">=")
    lt = _const("<")
    lte = _const("<=")
    regex = _const("~=")
    like = _const("like")
    is_ = _const("is")
    is_not = _const("is_not")

    def string(self, args):
        return args[0].value[1:-1]

    def number(self, args):
        return float(args[0].value)

    def field(self, args):
        return args[0].value

    def rule(self, args):
        return Q(tuple(args))

    def expression(self, args):
        return args[0]

    def or_expression(self, args):
        return args[0] | args[1]

    def and_expression(self, args):
        return args[0] & args[1]


def query_to_sql(query: str):
    query_parser = Lark(GRAMMAR, start="expression")
    tree = query_parser.parse(query)
    return QueryToQ().transform(tree).expression

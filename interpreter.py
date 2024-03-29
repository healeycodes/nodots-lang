from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict
import typing
from lark import Lark, Tree as LarkTree, Token as LarkToken
from grammar import GRAMMAR

parser = Lark(
    GRAMMAR,
    start="program",
    parser="lalr",
    keep_all_tokens=True,
    propagate_positions=True,
)

Meta = typing.NamedTuple("Meta", [("line", int), ("column", int)])


def format_number(seconds: float) -> str:
    if seconds >= 1:
        return f"{round(seconds, 1)}s"
    elif seconds >= 0.001:
        return f"{int(seconds * 1000)}ms"
    return f"{int(seconds * 1000 * 1000)}µs"


class Tree:
    kind = "tree"

    def __init__(self, data: str, meta: Meta, children: List[Tree | Token]) -> None:
        self.data = data
        self.meta = meta
        self.children = children

    def __str__(self) -> str:
        return f"{self.data} (node)"


class Token:
    kind = "token"
    data = "token"
    children: List[Any] = []

    def __init__(self, value: str, meta: Meta) -> None:
        self.value = value
        self.meta = meta

    def __eq__(self, other) -> bool:
        return self.value == other

    def __str__(self) -> str:
        return self.value


def print_tree(node: Tree | Token, depth=0):
    print(depth * "-" + f" {node}")
    if node.kind == "tree":
        for child in node.children:
            print_tree(child, depth + 1)


def build_nodots_tree(children: List[LarkTree | LarkToken]) -> List[Tree | Token]:
    return [
        Tree(
            str(child.data),
            Meta(child.meta.line, child.meta.column),
            build_nodots_tree(child.children),
        )
        if isinstance(child, LarkTree)
        else Token(child.value, Meta(child.line, child.column))  # type: ignore
        for child in children
    ]


class LanguageError(Exception):
    def __init__(self, line: int, column: int, message: str):
        self.line = line
        self.column = column
        self.message = message

    def __str__(self) -> str:
        return f"{self.line}:{self.column} [error] {self.message}"


class CallsDict(TypedDict):
    calls: List[Tuple[int, float]]


class Context:
    def __init__(
        self,
        parent,
        opts={"debug": False, "profile": False},
        line_durations: Optional[CallsDict] = None,
    ):
        self._opts = opts
        self.parent = parent
        self.children: List[Context] = []
        self.debug = opts["debug"]
        self.profile = opts["profile"]
        self.lookup = {}
        self.line_durations: CallsDict = line_durations or {"calls": []}

    def set(self, key, value):
        if self.debug:
            print(f"set: {key}, {value}")
        cur = self
        while cur:
            if key in cur.lookup:
                cur.lookup[key] = value
                return
            cur = cur.parent
        self.lookup[key] = value

    def get(self, line, column, key) -> Value:
        cur = self
        while cur:
            if key in cur.lookup:
                return cur.lookup[key]
            cur = cur.parent
        raise LanguageError(line, column, f"unknown variable '{key}'")

    def get_child_context(self):
        child = Context(self, self._opts, self.line_durations)
        self.children.append(child)
        return child

    def track_call(self, line, duration):
        if self.profile:
            self.line_durations["calls"].append((line, duration))

    def print_line_profile(self, source: str):
        line_durations: Dict[int, List[float]] = {}
        for ln, dur in self.line_durations["calls"]:
            if ln in line_durations:
                line_durations[ln].append(dur)
            else:
                line_durations[ln] = [dur]

        # convert raw durations into statistics
        line_info: Dict[int, List[str]] = {}
        for ln, line in enumerate(source.splitlines()):
            if ln in line_durations:
                line_info[ln] = [
                    # ncalls
                    f"x{len(line_durations[ln])}",
                    # tottime
                    f"{format_number(sum(line_durations[ln]))}",
                    # percall
                    f"{format_number((sum(line_durations[ln]) / len(line_durations[ln])))}",
                ]

        # configure padding/lining up columns
        padding = 2
        max_line = max([len(line) for line in source.splitlines()])
        max_digits = (
            max(
                [
                    max([len(f"{digits}") for digits in info])
                    for info in line_info.values()
                ]
            )
            + 3  # column padding
        )

        # iterate source code, printing the line and (if any) its statistics
        print(" " * (max_line + padding), "ncalls ", "tottime ", "percall ")
        for i, line in enumerate(source.splitlines()):
            output = line
            ln = i + 1
            if ln in line_info:
                output += " " * (max_line - len(line) + padding)
                ncalls = line_info[ln][0]
                cumtime = line_info[ln][1]
                percall = line_info[ln][2]
                output += ncalls + " " * (max_digits - len(ncalls))
                output += cumtime + " " * (max_digits - len(cumtime))
                output += percall + " " * (max_digits - len(percall))
            print(output)


class Value:
    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return f"({self.__class__.__name__}: {self.value})"

    def equals(self, other):
        return BoolValue(self.value == other.value)

    def not_equals(self, other):
        return BoolValue(self.value != other.value)

    def check_type(self, line, col, some_type_or_types: str | List[str], message):
        if type(some_type_or_types) == str:
            if self.__class__.__name__ != some_type_or_types:
                raise LanguageError(line, col, f"[{self}] {message}")
        else:
            for some_type in some_type_or_types:
                if self.__class__.__name__ == some_type:
                    return
            raise LanguageError(line, col, f"[{self}] {message}")

    def call_as_func(self, line, col, arguments) -> Value:
        self.check_type(line, col, "FunctionValue", "only functions are callable")
        try:
            return self.value(line, col, arguments)
        except RecursionError:
            raise LanguageError(line, col, "maximum recursion depth exceeded")


class BoolValue(Value):
    pass


class NilValue(Value):
    pass


class NumberValue(Value):
    pass


class StringValue(Value):
    pass


class FunctionValue(Value):
    pass


class DictValue(Value):
    value: Dict[str, Value]
    pass


class ListValue(Value):
    value: List[Value]
    pass


class ReturnEscape(Exception):
    def __init__(self, value: Value):
        self.value = value


class BreakEscape(Exception):
    pass


class ContinueEscape(Exception):
    pass


def format_value(value: Value):
    # TODO: complete this function for all value types
    if type(value) == NilValue:
        return "nil"
    elif type(value) == ListValue:
        return [format_value(v) for v in value.value]
    return value.value


def log(line: int, col: int, values: List[Value]):
    for v in values:
        print(format_value(v))


def dictionary(line: int, col: int, values: List[Value]):
    if len(values) % 2 != 0:
        raise LanguageError(
            line,
            col,
            f"dict expects an even number of args e.g. `k, v, k, v`, got: {list(map(lambda x: str(x), values))}",
        )

    ret = DictValue({})
    for i in range(0, len(values), 2):
        key = values[i]
        try:
            key.check_type(
                line, col, "StringValue", "only strings or numbers can be keys"
            )
        except:
            key.check_type(
                line, col, "NumberValue", "only strings or numbers can be keys"
            )
        value = values[i + 1]
        ret.value[key.value] = value
    return ret


def listof(line: int, col: int, values: List[Value]):
    return ListValue(values)


def mut(line: int, col: int, values: List[Value]) -> NilValue:
    if len(values) != 3:
        raise LanguageError(
            line,
            col,
            f"mut() expects three args (object, index, value), got {values}",
        )

    list_value: ListValue | None = None
    dict_value: DictValue | None = None
    try:
        values[0].check_type(
            line, col, "ListValue", "only dicts or lists can be called with mut()"
        )
        assert isinstance(values[0], ListValue)
        list_value = values[0]
    except:
        values[0].check_type(
            line, col, "DictValue", "only dicts or lists can be called with mut()"
        )
        assert isinstance(values[0], DictValue)
        dict_value = values[0]

    if list_value:
        values[1].check_type(
            line,
            col,
            "NumberValue",
            "lists can only be indexed by numbers",
        )
        index: int
        if values[1].value < 0 or not values[1].value.is_integer():
            raise LanguageError(
                line,
                col,
                f"list index must be a positive whole number, got: {values[1].value}",
            )
        if values[1].value >= len(list_value.value):
            raise LanguageError(
                line,
                col,
                f"list index out of bounds, len: {len(list_value.value)}, got: {values[1].value}",
            )
        index = int(values[1].value)
        list_value.value[index] = values[2]
        return NilValue(None)

    if dict_value:
        key: str
        try:
            values[1].check_type(
                line,
                col,
                "StringValue",
                "lists can only be indexed by strings or numbers",
            )
            key = values[1].value
        except:
            values[1].check_type(
                line,
                col,
                "NumberValue",
                "lists can only be indexed by strings or numbers",
            )
            key = str(values[1].value)
        dict_value.value[key] = values[2]
    return NilValue(None)


def at(line: int, col: int, values: List[Value]) -> Value:
    if len(values) != 2:
        raise LanguageError(
            line,
            col,
            f"at() expects two args (index, value), got {values}",
        )

    list_value: ListValue | None = None
    dict_value: DictValue | None = None
    try:
        values[0].check_type(
            line, col, "ListValue", "only dicts or lists can be called with mut()"
        )
        assert isinstance(values[0], ListValue)
        list_value = values[0]
    except:
        values[0].check_type(
            line, col, "DictValue", "only dicts or lists can be called with mut()"
        )
        assert isinstance(values[0], DictValue)
        dict_value = values[0]

    if list_value:
        values[1].check_type(
            line,
            col,
            "NumberValue",
            "lists can only be indexed by numbers",
        )
        index: int
        if values[1].value < 0 or not values[1].value.is_integer():
            raise LanguageError(
                line,
                col,
                f"list index must be a positive whole number, got: {values[1].value}",
            )
        if values[1].value >= len(list_value.value):
            raise LanguageError(
                line,
                col,
                f"list index out of bounds, len: {len(list_value.value)} got: {values[1].value}",
            )

        index = int(values[1].value)
        return list_value.value[index]

    if dict_value:
        key: str
        try:
            values[1].check_type(
                line,
                col,
                "StringValue",
                "lists can only be indexed by strings or numbers",
            )
            key = values[1].value
        except:
            values[1].check_type(
                line,
                col,
                "NumberValue",
                "lists can only be indexed by strings or numbers",
            )
            key = str(values[1].value)
        if not key in dict_value.value:
            return NilValue(None)
        return dict_value.value[key]

    raise Exception("unreachable")


def keysof(line: int, col: int, values: List[Value]) -> ListValue:
    if len(values) != 1:
        raise LanguageError(
            line,
            col,
            f"keys() expects one arg (dict), got {values}",
        )
    values[0].check_type(
        line,
        col,
        "DictValue",
        "only dicts can be called with keys()",
    )
    return ListValue([StringValue(k) for k in values[0].value.keys()])


def vals(line: int, col: int, values: List[Value]) -> ListValue:
    if len(values) != 1:
        raise LanguageError(
            line,
            col,
            f"vals() expects one arg (dict), got {values}",
        )
    values[0].check_type(
        line,
        col,
        "DictValue",
        "only dicts can be called with vals()",
    )
    return ListValue(list(values[0].value.values()))


def read(line: int, col: int, values: List[Value]) -> Value:
    chunk_size = 1024
    if len(values) != 2:
        raise LanguageError(
            line,
            col,
            f"read() expects two args [string, function], got {values}",
        )
    values[0].check_type(
        line,
        col,
        "StringValue",
        f"read() expects a string file path as the first arg, got {values[0]}",
    )
    values[1].check_type(
        line,
        col,
        "FunctionValue",
        f"read() expects a read function as the second arg, got {values[1]}",
    )
    file_path = values[0].value
    read_function = values[1]
    try:
        with open(file_path, "r") as f:
            while True:
                b = f.read(chunk_size)
                read_function.call_as_func(line, col, [StringValue(b)])
                if b == "":
                    break
    except Exception as e:
        raise LanguageError(line, col, f'error reading "{file_path}": (py: {e})')
    return StringValue("")


def write(line: int, col: int, values: List[Value]) -> Value:
    if len(values) != 2:
        raise LanguageError(
            line,
            col,
            f"write() expects two args [string, string | number], got {values}",
        )
    values[0].check_type(
        line,
        col,
        "StringValue",
        f"write() expects a (string) file path as the first arg, got {values[0]}",
    )
    values[1].check_type(
        line,
        col,
        ["StringValue", "NumberValue"],
        f"write() expects a (string | number) as the second arg, got {values[1]}",
    )
    file_path = values[0].value
    try:
        with open(file_path, "a") as f:
            f.write(values[1].value)
    except Exception as e:
        raise LanguageError(line, col, f'error writing "{file_path}": (py: {e})')
    return NilValue(None)


def join(line: int, col: int, values: List[Value]) -> Value:
    if len(values) != 2:
        raise LanguageError(
            line,
            col,
            f"join() expects two args [string, string] or [list, list], got {values}",
        )

    # (string, string)
    if values[0].__class__.__name__ == "StringValue":
        if values[0].__class__.__name__ != "StringValue":
            raise LanguageError(
                line,
                col,
                f"join() expects two args [string, string] or [list, list], got {values}",
            )
        return StringValue(values[0].value + values[1].value)
    elif values[0].__class__.__name__ == "ListValue":
        if values[0].__class__.__name__ != "ListValue":
            raise LanguageError(
                line,
                col,
                f"join() expects two args [string, string] or [list, list], got {values}",
            )
        ret = []
        for v in values[0].value:
            ret.append(v)
        for v in values[1].value:
            ret.append(v)
        return ListValue(ret)
    raise LanguageError(
        line,
        col,
        f"join() expects two args [string, string] or [list, list], got {values}",
    )


def length(line: int, col: int, values: List[Value]) -> Value:
    if len(values) != 1:
        raise LanguageError(
            line,
            col,
            f"len() expects a single arg (string | list), got {values}",
        )
    values[0].check_type(
        line,
        col,
        ["StringValue", "ListValue"],
        f"len() expects a (string | list)",
    )
    return NumberValue(len(values[0].value))


def key_from_identifier_node(node: Tree | Token) -> str:
    # we're not looking for the idenitifier's "reference"
    # when we context.set, we will update the lookup table
    # so we can just dig the literal string value here
    return node.children[0].value  # type: ignore


def eval_identifier(node: Any, context: Context):
    return context.get(node.meta.line, node.meta.column, node.children[0].value)


def eval_primary(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_identifier(node.children[0], context)
    # 0th is '(' and 2nd is ')'
    if node.children[1].data == "expression":
        return eval_expression(node.children[1], context)
    raise Exception("unreachable")


def eval_arguments(node: Tree | Token, context: Context) -> List[Value]:
    return [
        eval_expression(child, context)
        for child in node.children
        # filter out '(' and ')'
        if child.kind == "tree"
    ]


def eval_call(node: Tree | Token, context: Context) -> Value:
    # primary aka not a function call
    if len(node.children) == 1:
        for child in node.children:
            if child.data == "true":
                return BoolValue(True)
            elif child.data == "false":
                return BoolValue(False)
            elif child.data == "primary":
                return eval_primary(child, context)
            elif child.data == "number":
                first_child_num: Any = child.children[0]
                return NumberValue(float(first_child_num.value))
            elif child.data == "nil":
                return NilValue(None)
            elif child.data == "string":
                # trim quote marks `"1"` -> `1`
                first_child_str: Any = child.children[0]
                return StringValue(first_child_str.value[1:-1])
        raise Exception("unreachable")

    start = time.perf_counter()

    # functions calls can be chained like `a()()(2)`
    # so we want the initial function and then an
    # arbitrary number of calls (with or without arguments)
    current_func = eval_primary(node.children[0], context)

    i = 0
    arguments: List[None | Tree | Token] = []
    while i < len(node.children) - 1:
        i += 1
        if node.children[i] == ")":
            if node.children[i - 1] == "(":
                arguments.append(None)
            elif (
                node.children[i - 1].kind == "tree"
                and node.children[i - 1].data == "arguments"
            ):
                arguments.append(node.children[i - 1])
            else:
                raise Exception("unreachable")

    for args in arguments:
        start = time.perf_counter()
        current_func = current_func.call_as_func(
            node.children[0].meta.line,
            node.children[0].meta.column,
            eval_arguments(args, context) if args else [],
        )
        context.track_call(node.children[0].meta.line, time.perf_counter() - start)

    return current_func


def eval_unary(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_call(node.children[0], context)
    op = node.children[0]
    left = eval_unary(node.children[1], context)

    if op == "-":
        left.check_type(
            node.children[1].meta.line,
            node.children[1].meta.column,
            "NumberValue",
            "only numbers can be negated",
        )
        return NumberValue(-left.value)
    if op == "!":
        left.check_type(
            node.children[1].meta.line,
            node.children[1].meta.column,
            "BoolValue",
            "only booleans can be flipped",
        )
        # TODO: maybe a method on Value or BoolValue instead?
        return BoolValue(not left.value)
    raise Exception("unreachable")


def eval_factor(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_unary(node.children[0], context)
    left = eval_unary(node.children[0], context)
    op = node.children[1]
    right = eval_unary(node.children[2], context)
    left.check_type(
        node.children[0].meta.line,
        node.children[0].meta.column,
        "NumberValue",
        "only numbers can be factored",
    )
    right.check_type(
        node.children[2].meta.line,
        node.children[2].meta.column,
        "NumberValue",
        "only numbers can be factored",
    )
    if op == "*":
        return NumberValue(left.value * right.value)
    elif op == "/":
        try:
            return NumberValue(left.value / right.value)
        except ZeroDivisionError:
            raise LanguageError(
                node.children[0].meta.line,
                node.children[0].meta.column,
                "cannot divide by zero",
            )
    raise Exception("unreachable")


def eval_term(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_factor(node.children[0], context)
    left = eval_factor(node.children[0], context)
    op = node.children[1]
    right = eval_factor(node.children[2], context)
    left.check_type(
        node.children[0].meta.line,
        node.children[0].meta.column,
        "NumberValue",
        "only numbers can be added or subtracted",
    )
    right.check_type(
        node.children[2].meta.line,
        node.children[2].meta.column,
        "NumberValue",
        "only numbers can be added or subtracted",
    )
    if op == "+":
        return NumberValue(left.value + right.value)
    elif op == "-":
        return NumberValue(left.value - right.value)
    raise Exception("unreachable")


def eval_comparison(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_term(node.children[0], context)
    left = eval_term(node.children[0], context)
    op = node.children[1]
    right = eval_term(node.children[2], context)
    left.check_type(
        node.children[0].meta.line,
        node.children[0].meta.column,
        "NumberValue",
        "only numbers can be compared",
    )
    right.check_type(
        node.children[2].meta.line,
        node.children[2].meta.column,
        "NumberValue",
        "only numbers can be compared",
    )
    if op == "<":
        return BoolValue(left.value < right.value)
    elif op == "<=":
        return BoolValue(left.value <= right.value)
    elif op == ">":
        return BoolValue(left.value > right.value)
    elif op == ">=":
        return BoolValue(left.value >= right.value)
    raise Exception("unreachable")


def eval_equality(node: Tree | Token, context: Context) -> Value:
    if len(node.children) == 1:
        return eval_comparison(node.children[0], context)

    left = eval_comparison(node.children[0], context)
    op = node.children[1]
    right = eval_comparison(node.children[2], context)
    if op == "==":
        return left.equals(right)
    elif op == "!=":
        return left.not_equals(right)
    raise Exception("unreachable")


def eval_logic_and(node: Tree | Token, context: Context) -> Value | BoolValue:
    if len(node.children) == 1:
        return eval_equality(node.children[0], context)
    left = eval_equality(node.children[0], context)
    op = node.children[1]
    right = eval_equality(node.children[2], context)
    left.check_type(
        node.children[0].meta.line,
        node.children[0].meta.column,
        "BoolValue",
        "only booleans can be used with 'and'",
    )
    right.check_type(
        node.children[2].meta.line,
        node.children[2].meta.column,
        "BoolValue",
        "only booleans can be used with 'and'",
    )

    if op == "and":
        return BoolValue(left.value and right.value)
    raise Exception("unreachable")


def eval_logic_or(node: Tree | Token, context: Context) -> Value | BoolValue:
    if len(node.children) == 1:
        return eval_logic_and(node.children[0], context)
    left = eval_logic_and(node.children[0], context)
    op = node.children[1]
    right = eval_logic_and(node.children[2], context)
    left.check_type(
        node.children[0].meta.line,
        node.children[0].meta.column,
        "BoolValue",
        "only booleans can be used with 'or'",
    )
    right.check_type(
        node.children[2].meta.line,
        node.children[2].meta.column,
        "BoolValue",
        "only booleans can be used with 'or'",
    )

    if op == "or":
        return BoolValue(left.value or right.value)
    raise Exception("unreachable")


def eval_assignment(node: Tree | Token, context: Context) -> NilValue | Value:
    if node.children[0].data == "identifier":
        key = key_from_identifier_node(node.children[0])
        value = eval_assignment(node.children[2], context)
        context.set(key, value)
        return NilValue(None)
    elif node.children[0].data == "logic_or":
        return eval_logic_or(node.children[0], context)
    raise Exception("unreachable")


def eval_expression(node: Tree | Token, context: Context) -> Value:
    for child in node.children:
        if child.data == "assignment":
            return eval_assignment(child, context)
    raise Exception("unreachable")


def eval_expression_stmt(node: Tree | Token, context: Context) -> Value:
    # support empty expression stmts
    for child in node.children:
        if child.kind == "tree":
            return eval_expression(child, context)
    return NilValue(None)


def eval_return_stmt(node: Tree | Token, context: Context):
    for child in node.children:
        # filter out syntax like `return` and `;`
        if child.kind == "tree":
            raise ReturnEscape(eval_expression(child, context))
    # handle `return;``
    raise ReturnEscape(NilValue(None))


def eval_if_stmt(node: Tree | Token, context: Context):
    # the tree shape is as follows (any number of childs)
    # ['if', '(', expr, ')', child_1, child_2, 'fi']
    if_check = eval_expression(node.children[2], context)
    if_check.check_type(
        node.meta.line, node.meta.column, "BoolValue", "if expressions expect a boolean"
    )
    if if_check.value != True:
        return NilValue(None)
    start, end = node.children.index(")") + 1, node.children.index("fi")  # type: ignore
    for decl in node.children[start:end]:
        eval_declaration(decl, context)
    return NilValue(None)


def eval_for_stmt(node: Tree | Token, context: Context):
    for_context = context.get_child_context()
    parts: List[Tree] = []
    for child in node.children:
        if child.kind == "tree":
            parts.append(child)  # type: ignore
    initial_expr_stmt, limit_expr_stmt, increment_expr = parts[:3]
    eval_expression_stmt(initial_expr_stmt, for_context)

    while True:
        limit_check = eval_expression_stmt(limit_expr_stmt, for_context)
        limit_check.check_type(
            limit_expr_stmt.meta.line,
            limit_expr_stmt.meta.column,
            "BoolValue",
            "expected boolean",
        )
        if not limit_check.value:
            break
        for decl_expr in parts[3:]:
            try:
                eval_declaration(decl_expr, for_context)
            except BreakEscape:
                return NilValue(None)
            except ContinueEscape:
                break
        eval_expression(increment_expr, for_context)
    return NilValue(None)


def eval_statement(node: Tree | Token, context: Context) -> Value:
    for child in node.children:
        if child.data == "expression_stmt":
            return eval_expression_stmt(child, context)
        elif child.data == "return_stmt":
            return eval_return_stmt(child, context)
        elif child.data == "if_stmt":
            return eval_if_stmt(child, context)
        elif child.data == "for_stmt":
            return eval_for_stmt(child, context)
        elif child.data == "break_stmt":
            raise BreakEscape()
        elif child.data == "continue_stmt":
            raise ContinueEscape()
    raise Exception("unreachable")


def eval_parameters(node: Tree | Token, context: Context) -> List[str]:
    parameters = []
    for child in node.children:
        if child.kind == "tree" and child.data == "identifier":
            parameters.append(key_from_identifier_node(child))
    return parameters


def eval_function(node: Tree | Token, context: Context) -> NilValue:
    function_context = context.get_child_context()
    key = key_from_identifier_node(node.children[0])

    parameters = []
    if node.children.index(")") - node.children.index("(") == 2:  # type: ignore
        parameters = eval_parameters(
            node.children[node.children.index("(") + 1],
            context,  # type: ignore
        )
    body = node.children[node.children.index(")") + 1 :]  # type: ignore

    def function(line, col, arguments):
        if len(arguments) != len(parameters):
            raise LanguageError(
                line,
                col,
                "not enough (or too many) function arguments, "
                + f"want {len(parameters)}, got {len(arguments)}",
            )
        per_call_context = function_context.get_child_context()
        for i, arg in enumerate(arguments):
            per_call_context.set(parameters[i], arg)
        for child in body:
            try:
                eval_declaration(child, per_call_context)
            except ReturnEscape as e:
                return e.value
            except BreakEscape:
                raise LanguageError(
                    child.meta.line,
                    child.meta.column,
                    "can't use 'break' outside of for loop body",
                )
            except ContinueEscape:
                raise LanguageError(
                    child.meta.line,
                    child.meta.column,
                    "can't use 'continue' outside of for loop body",
                )
        return NilValue(None)

    context.set(key, FunctionValue(function))
    return NilValue(None)


def eval_fun_decl(node: Tree | Token, context: Context):
    # 0th is 'fun', 2nd is 'nuf'
    return eval_function(node.children[1], context)


def eval_declaration(node: Tree | Token, context: Context):
    for child in node.children:
        if child.data == "statement":
            return eval_statement(child, context)
        elif child.data == "fun_decl":
            return eval_fun_decl(child, context)
    raise Exception("unreachable")


def eval_program(node: Tree | Token, context: Context):
    last: NilValue | Value = NilValue(None)
    for child in node.children:
        try:
            last = eval_declaration(child, context)
        except BreakEscape:
            raise LanguageError(
                child.meta.line,
                child.meta.column,
                "can't use 'break' outside of for loop body",
            )
        except ContinueEscape:
            raise LanguageError(
                child.meta.line,
                child.meta.column,
                "can't use 'continue' outside of for loop body",
            )
    return last


def inject_builtins(context: Context):
    funcs = {
        "log": log,
        "dict": dictionary,
        "list": listof,
        "mut": mut,
        "at": at,
        "keys": keysof,
        "vals": vals,
        "read": read,
        "write": write,
        "join": join,
        "len": length,
    }
    for name, func in funcs.items():
        context.set(name, FunctionValue(func))


def inject_std_lib(context: Context):
    source = """
    fun read_all(file_path)
        ret = "";
        fun each_chunk(chunk)
            ret = join(ret, chunk);
        nuf
        read(file_path, each_chunk);
        return ret;
    nuf
    """
    root = build_nodots_tree([parser.parse(source)])[0]
    eval_program(root, context=context)


def inject_all(context: Context):
    inject_builtins(context)
    inject_std_lib(context)


def get_root(source: str):
    try:
        parsed = parser.parse(source)
    except Exception as e:
        # Usually everything after the first line isn't helpful for a user
        # TODO: surface the full parser error during development
        raise Exception(f"{e}".split("\n")[0])
    return build_nodots_tree([parsed])[0]


def get_context(opts: Dict[str, bool]) -> Context:
    root_context = Context(None, opts=opts)
    inject_all(root_context)
    return root_context


def interpret(source: str, opts={}):
    opts = {"debug": False, "profile": False} | opts
    try:
        root_context = get_context(opts)
        root = get_root(source)
        result = eval_program(root, context=root_context)
        if opts["profile"]:
            root_context.print_line_profile(source)
        return result
    except LanguageError as e:
        return e

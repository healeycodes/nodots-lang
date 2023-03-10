from __future__ import annotations
from typing import Any, List
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


class Context:
    def __init__(self, parent, opts={"debug": False}):
        self._opts = opts
        self.parent = parent
        self.debug = opts["debug"]
        self.lookup = {}

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
        return Context(self, self._opts)


class Value:
    def __init__(self, value):
        self.value = value

    def __str__(self) -> str:
        return f"({self.__class__.__name__}: {self.value})"

    def equals(self, other):
        return BoolValue(self.value == other.value)

    def not_equals(self, other):
        return BoolValue(self.value != other.value)

    def check_type(self, line, col, some_type, message):
        if self.__class__.__name__ != some_type:
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


class ReturnEscape(Exception):
    def __init__(self, value: Value):
        self.value = value


class BreakEscape(Exception):
    pass


class ContinueEscape(Exception):
    pass


def log(line: int, col: int, values: List[Value]):
    for v in values:
        print(v.value)


def inject_standard_library(context: Context):
    for func in [
        log,
    ]:
        context.set(func.__name__, FunctionValue(func))


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
        current_func = current_func.call_as_func(
            node.children[0].meta.line,
            node.children[0].meta.column,
            eval_arguments(args, context) if args else [],
        )

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
            node.children[node.children.index("(") + 1], context  # type: ignore
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


def interpret(source: str, opts={"debug": True}):
    root_context = Context(None, opts=opts)
    inject_standard_library(root_context)
    try:
        root = build_nodots_tree([parser.parse(source)])[0]
        result = eval_program(root, context=root_context)
        return result
    except LanguageError as e:
        return e

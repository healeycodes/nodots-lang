from typing import Dict, List, Tuple, Type, Union
from lark import Lark, Tree, Token
from grammar_static import GRAMMAR

parser = Lark(
    GRAMMAR,
    start="program",
    parser="lalr",
    keep_all_tokens=True,
    propagate_positions=True,
)


class I32:
    def __str__(self):
        return "i32"


class F64:
    def __str__(self):
        return "f64"


Params = List[Tuple[str, Union[Type[I32], Type[F64]]]]


def format_params(params: Params):
    return "(" + (", ".join(map(lambda p: f"{p[1]} {p[0]}", params))) + ")"


class Func:
    def __init__(
        self,
        params: Params,
        ntype: Union[Type[I32], Type[F64]],
    ):
        self.params = params
        self.ntype = ntype

    def __str__(self):
        return f"func ({format_params(self.params)}) -> {self.ntype}"


def ntype_to_class(ntype: str):
    if ntype == "i32":
        return I32()
    elif ntype == "f64":
        return F64()
    raise Exception(f"unknown ntype {ntype}")


Ntype = Union[Type[I32], Type[F64], Type[Func]]


class Context:
    scope: Dict[str, Ntype] = {}
    func_return_ntype: None | Ntype = None
    wat = "(module\n"

    def write(self, code: str):
        self.wat += f"{code}"

    def finish(self):
        self.wat += ")\n"
        return self.wat


def visit_functions(node: Tree, context):
    for child in node.children:
        if isinstance(child, Token):
            continue
        if child.data == "fun_stmt":
            visit_fun_stmt_for_types(child, context)
        else:
            visit_functions(child, context)


def visit_declaration(node: Tree, context: Context):
    for child in node.children:
        if child.data == "expression_stmt":
            visit_expression_stmt(child, context)
        elif child.data == "fun_stmt":
            visit_fun_stmt(child, context)
        elif child.data == "return_stmt":
            visit_return_stmt(child, context)
        elif child.data == "if_stmt":
            visit_if_stmt(child, context)


def visit_expression_stmt(node: Tree, context: Context):
    for child in node.children:
        if child == ";":
            continue
        if child.data == "expression":
            visit_expression(child, context)


def visit_expression(node: Tree, context: Context) -> Ntype:
    line, col = node.meta.line, node.meta.column
    if node.children[0].data == "type":
        identifier = node.children[1].children[0].value
        if identifier in context.scope:
            raise Exception(f"can't redeclare identifier: {identifier} ({line}:{col})")

        context.write(f"(local ${identifier} {node.children[0].children[0]})\n")
        expr_ntype = visit_expression(node.children[3], context)
        context.write(f"(local.set ${identifier})\n")

        context.scope[identifier] = expr_ntype
        return expr_ntype
    elif node.children[0].data == "identifier":
        identifier = node.children[0].children[0].value
        if identifier not in context.scope:
            raise Exception(f"unknown identifier: {identifier} ({line}:{col})")
        ntype = context.scope[identifier]

        expr_ntype = visit_expression(node.children[2], context)
        context.write(f"(local.set ${identifier})\n")

        if type(ntype) != type(expr_ntype):
            raise Exception(
                f"type error {identifier}: expected {ntype} got {expr_ntype} ({line}:{col})"
            )
        return expr_ntype

    return visit_equality(node.children[0], context)


def visit_equality(node: Tree, context: Context) -> Ntype:
    if len(node.children) == 1:
        return visit_comparison(node.children[0], context)
    line, col = node.meta.line, node.meta.column

    op = "eq" if node.children[1] == "==" else "ne"
    left_nytpe = visit_comparison(node.children[0], context)
    right_nytpe = visit_comparison(node.children[2], context)

    if type(left_nytpe) != type(right_nytpe):
        raise Exception(
            f"type error {node.children[1]}: mismatched types got {left_nytpe} and {right_nytpe} ({line}:{col})"
        )
    context.write(f"({left_nytpe}.{op})\n")
    return left_nytpe


def visit_comparison(node: Tree, context: Context) -> Ntype:
    if len(node.children) == 1:
        return visit_term(node.children[0], context)
    line, col = node.meta.line, node.meta.column

    if node.children[1] == "<":
        op = "lt"
    elif node.children[1] == "<=":
        op = "le"
    elif node.children[1] == ">":
        op = "gt"
    elif node.children[1] == ">=":
        op = "ge"

    left_nytpe = visit_term(node.children[0], context)
    right_nytpe = visit_term(node.children[2], context)

    if type(left_nytpe) != type(right_nytpe):
        raise Exception(
            f"type error {node.children[1]}: mismatched types got {left_nytpe} and {right_nytpe} ({line}:{col})"
        )
    context.write(f"({left_nytpe}.{op})\n")
    return left_nytpe


def visit_term(node: Tree, context: Context) -> Ntype:
    if len(node.children) == 1:
        return visit_factor(node.children[0], context)
    line, col = node.meta.line, node.meta.column

    op = "add" if node.children[1] == "+" else "sub"
    left_nytpe = visit_factor(node.children[0], context)
    right_nytpe = visit_factor(node.children[2], context)

    if type(left_nytpe) != type(right_nytpe):
        raise Exception(
            f"type error {node.children[1]}: mismatched types got {left_nytpe} and {right_nytpe} ({line}:{col})"
        )
    context.write(f"({left_nytpe}.{op})\n")
    return left_nytpe


def visit_factor(node: Tree, context: Context) -> Ntype:
    if len(node.children) == 1:
        return visit_call(node.children[0], context)
    line, col = node.meta.line, node.meta.column

    op = "mul" if node.children[1] == "*" else "div"
    left_nytpe = visit_call(node.children[0], context)
    right_nytpe = visit_call(node.children[2], context)

    if type(left_nytpe) != type(right_nytpe):
        raise Exception(
            f"type error {node.children[1]}: mismatched types got {left_nytpe} and {right_nytpe} ({line}:{col})"
        )
    context.write(f"({left_nytpe}.{op})\n")
    return left_nytpe


def visit_call(node: Tree, context: Context) -> Ntype:
    if len(node.children) == 1:
        return visit_primary(node.children[0], context)
    line, col = node.meta.line, node.meta.column

    identifier = node.children[0].children[0].children[0]
    if identifier not in context.scope:
        raise Exception(f"unknown function: {identifier} ({line}:{col})")

    func = context.scope[identifier]
    if type(func) != Func:
        raise Exception(f"can only call functions: {identifier} ({line}:{col})")

    args = []
    if not isinstance(node.children[2], Token):
        args = list(
            filter(lambda arg: not isinstance(arg, Token), node.children[2].children)
        )

    if len(func.params) != len(args):
        raise Exception(
            f"type error {identifier}: expected {len(func.params)} args got {len(args)} ({line}:{col})"
        )

    context.write(f"(call ${identifier} ")
    for i, arg in enumerate(args):
        if isinstance(arg, Token):
            continue
        arg_ntype = visit_expression(arg, context)
        if type(arg_ntype) != type(func.params[i][1]):
            raise Exception(
                f"type error {identifier}: expected {format_params(func.params)} got {arg_ntype} at pos {i} ({line}:{col})"
            )
    context.write(")\n")
    return func.ntype


def visit_primary(node: Tree, context: Context) -> Ntype:
    line, col = node.meta.line, node.meta.column
    inner = node.children[0]
    if isinstance(inner, Token):
        if "." in inner:
            context.write(f"(f64.const {inner})\n")
            return F64()
        else:
            context.write(f"(i32.const {inner})\n")
            return I32()
    if inner.data == "identifier":
        identifier = inner.children[0]
        if identifier in context.scope:
            context.write(f"(local.get ${identifier})\n")
            return context.scope[identifier]
        raise Exception(f"unknown identifier: {identifier} ({line}:{col})")
    raise Exception("unreachable")


def visit_fun_stmt_for_types(node: Tree, context: Context):
    line, col = node.meta.line, node.meta.column
    func_parts = node.children[1].children
    identifier = func_parts[0].children[0].value
    if identifier in context.scope:
        raise Exception(f"can't redeclare identifier: {identifier} ({line}:{col})")

    ntype: None | Tree = None
    args: None | Tree = None
    i = 0
    while i < len(func_parts):
        if func_parts[i] == "(" and func_parts[i + 1] != ")":
            args = func_parts[i + 1].children
        if func_parts[i] == "->":
            ntype = ntype_to_class(func_parts[i + 1].children[0].value)
        i += 1

    if not ntype:
        raise Exception(f"missing ntype for function {identifier} ({line}:{col})")

    params: Params = []
    if args:
        param_parts = list(filter(lambda x: x != ",", func_parts[2].children))
        for i in range(0, len(param_parts), 2):
            param_ntype = ntype_to_class(param_parts[i].children[0])
            param_id = param_parts[i + 1].children[0]
            params.append((param_id, param_ntype))
    context.scope[identifier] = Func(params, ntype)


def visit_fun_stmt(node: Tree, context: Context):
    line, col = node.meta.line, node.meta.column
    func_parts = node.children[1].children
    identifier = func_parts[0].children[0].value

    if identifier not in context.scope:
        raise Exception(
            f"could't find function (this really shouldn't happen): {identifier} ({line}:{col})"
        )
    func: Func = context.scope[identifier]
    if type(func) != Func:
        raise Exception(
            f"expected func to be of type Func (this really shouldn't happen): {identifier} ({line}:{col})"
        )

    bodies_idx = 0
    while bodies_idx < len(func_parts):
        if func_parts[bodies_idx] == "->":
            bodies_idx += 2
            break
        bodies_idx += 1
    func_bodies = func_parts[bodies_idx:]

    if context.func_return_ntype is not None:
        raise Exception(f"nesting functions isn't allowed: {identifier} ({line}:{col})")
    context.func_return_ntype = func.ntype

    func_scope = {}
    for param in func.params:
        func_scope[param[0]] = param[1]
    for id, maybe_func in context.scope.items():
        if type(maybe_func) == Func:
            func_scope[id] = maybe_func

    prev_scope = context.scope
    context.scope = func_scope
    wat_params = " ".join(map(lambda p: f"(param ${p[0]} {p[1]})", func.params))
    context.write(
        f'\n(func ${identifier} (export "{identifier}") {wat_params} (result {func.ntype})\n'
    )
    for func_body in func_bodies:
        visit_declaration(func_body, context)

    # write a default value to avoid type errors
    # functions without a return statement return the default value (e.g. `0`)
    context.write(f"({func.ntype}.const 0)")

    context.write(")\n\n")
    context.scope = prev_scope

    context.func_return_ntype = None


def visit_return_stmt(node: Tree, context: Context):
    line, col = node.meta.line, node.meta.column
    for child in node.children[1].children:
        if child == ";":
            continue
        if child.data == "expression":
            ntype = visit_expression(child, context)
            if context.func_return_ntype is None:
                raise Exception(f"can't return outside of functions ({line}:{col})")
            if type(ntype) != type(context.func_return_ntype):
                raise Exception(
                    f"type error return: expected {context.func_return_ntype} got {ntype} ({line}:{col})"
                )
    context.write("(return)\n")


def visit_if_stmt(node: Tree, context: Context):
    visit_expression(node.children[2], context)
    context.write(
        """(if
      (then\n"""
    )
    for i in range(3, len(node.children)):
        if isinstance(node.children[i], Token):
            continue
        visit_declaration(node.children[i], context)
    context.write(")\n)\n")


def compile(source: str, context: Context):
    root = parser.parse(source)
    visit_functions(root, context)
    visit_declaration(root, context)


if __name__ == "__main__":
    source = """
fn fib(i32 n) -> i32
  if (n == 0)
    return 0;
  fi
  if (n == 1)
    return 1;
  fi
  return fib(n - 1) + fib(n - 2);
nf
"""
    context = Context()
    compile(source, context)
    context.finish()
    print(context.wat)

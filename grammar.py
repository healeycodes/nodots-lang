GRAMMAR = r"""
    program         : declaration*

    declaration     : fun_decl | statement
    fun_decl        : "fun" function "nuf"

    statement       : expression_stmt | return_stmt | if_stmt | for_stmt
    expression_stmt : expression? ";"
    return_stmt     : "return" expression? ";"
    if_stmt         : "if" "(" expression ")" declaration* "fi"

    expression      : assignment
    assignment      : identifier "=" assignment | logic_or
    logic_or        : logic_and ( "or" logic_and )*
    logic_and       : equality ( "and" equality )*
    equality        : comparison ( ( "!=" | "==" ) comparison )*
    comparison      : term ( ( ">" | ">=" | "<" | "<=" ) term )*
    term            : factor ( ( "-" | "+" ) factor )*
    factor          : unary ( ( "/" | "*" ) unary )*
    unary           : ( "!" | "-" ) unary | call
    call            : primary ( "(" arguments? ")" )*
    primary         : "true" -> true | "false" -> false | "nil" -> nil
                      | NUMBER -> number | ESCAPED_STRING -> string
                      | identifier | "(" expression ")"

    function       : identifier "(" parameters? ")" declaration*
    parameters     : identifier ( "," identifier )*
    arguments      : expression ( "," expression )*

    identifier     : CNAME

    %import common.ESCAPED_STRING
    %import common.LETTER
    %import common.DIGIT
    %import common.NUMBER
    %import common.CNAME

    %import common.WS
    %ignore WS
    %import common.SH_COMMENT
    %ignore SH_COMMENT
    """

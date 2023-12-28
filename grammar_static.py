# similar to grammar.py but for a static typed version of nodots
GRAMMAR = r"""
    program         : fun_stmt*

    declaration     : fun_stmt | return_stmt | if_stmt | expression_stmt

    fun_stmt        : "fn" function "nf"
    return_stmt     : "return" expression_stmt
    if_stmt         : "if" "(" expression ")" declaration* "fi"
    expression_stmt : expression? ";"

    expression      : type? identifier "=" expression | equality
    equality        : comparison ( ( "!=" | "==" ) comparison )*
    comparison      : term ( ( ">" | ">=" | "<" | "<=" ) term )*
    term            : factor ( ( "-" | "+" ) factor )*
    factor          : call ( ( "/" | "*" ) call )*
    call            : primary ( "(" arguments? ")" )*
    primary         : NUMBER -> number | identifier

    function       : identifier "(" parameters? ")" "->" type declaration*
    parameters     : type identifier ( "," type identifier )*
    arguments      : expression ( "," expression )*

    type           : "i32" | "f64"
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

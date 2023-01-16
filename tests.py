from interpreter import NilValue, interpret

kitchen_sink_example = """
# booleans
(true or false) and !true;

# numbers!
(2 * 2) / 4 == 0;
1 < 2;
-(8 * 8) > -65;

# strings!
log("Hello, World!");

# variables!
some_var = 2;

# loops!
sum = 0;
for (i = 0; i < 5; i = i + 1)
  sum = sum + i;
rof
log(sum);

# functions!
fun some_func(b, c)
  return b * c;
nuf
some_func(some_var, 5);

# naive fibonacci
fun fib(x)
  if (x == 0 or x == 1)
    return x;
  fi
  return fib(x - 1) + fib(x - 2);
nuf
fib(10);

# closures!
fun closure()
  z = 0;
  fun inner()
    z = z + 1;
    return z;
  nuf
  return inner;
nuf
closure()(); # 1
"""


def assert_or_log(a, b):
    try:
        assert a == b
    except AssertionError as e:
        print(f"{a} != {b}")
        print("tests failed!")
        quit(1)


# example programs
assert_or_log(interpret(kitchen_sink_example).value, 1)

# basic types
assert_or_log(interpret("1;").value, 1)
assert_or_log(interpret("-1.5;").value, -1.5)
assert_or_log(interpret('"1";').value, "1")
assert_or_log(interpret("true;").value, True)
assert_or_log(interpret("false;").value, False)
assert_or_log(interpret("nil;").value, None)
assert_or_log(interpret("nil == nil;").value, True)

# logic
assert_or_log(interpret("true and true;").value, True)
assert_or_log(interpret("true and false;").value, False)
assert_or_log(interpret("true or false;").value, True)
assert_or_log(interpret("false or false;").value, False)
assert_or_log(interpret("(false or false) or true;").value, True)
assert_or_log(interpret("(false or false) and true;").value, False)
assert_or_log(interpret("a = nil; if (true) a = 2; fi a;").value, 2)
assert_or_log(interpret("a = nil; if (false or true) a = 2; fi a;").value, 2)
assert_or_log(
    interpret(
        """
fun truth()
  return true;
nuf a = nil;
if (truth())
  a = 2;
fi
a;
"""
    ).value,
    2,
)
assert_or_log(isinstance(interpret("a = nil; if (false) a = 2; fi a;"), NilValue), True)

# compare
assert_or_log(interpret("1 == 1;").value, True)
assert_or_log(interpret("1 != 1;").value, False)
assert_or_log(interpret("1 >= 1;").value, True)
assert_or_log(interpret("1 <= 1;").value, True)
assert_or_log(interpret("2 < 3;").value, True)
assert_or_log(interpret("3 > 2;").value, True)

# expressions
assert_or_log(isinstance(interpret(";"), NilValue), True)
assert_or_log(interpret("-1;").value, -1)
assert_or_log(isinstance(interpret("-1;;"), NilValue), True)
assert_or_log(interpret("(1);").value, 1)
assert_or_log(interpret("-(1);").value, -1)
assert_or_log(interpret("(1 + 1);").value, 2)
assert_or_log(interpret("(1 - 1);").value, 0)
assert_or_log(interpret("(2 * 2);").value, 4)
assert_or_log(interpret("(2 * 2) * (7 + 8);").value, 60)
assert_or_log(interpret("(1 / 1);").value, 1)
assert_or_log(interpret("a = (6 * 6); a;").value, 36)
assert_or_log(
    interpret(
        """
sum = 0;
for (i = 0; i < 5; i = i + 1)
  sum = sum + i;
rof
sum;
"""
    ).value,
    10,
)
assert_or_log(
    interpret(
        """
a = 0;
for (i = 0; i < 5; i = i + 1)
  a = a + 1;
  break;
rof
a;
"""
    ).value,
    1,
)
assert_or_log(
    interpret(
        """
a = 0;
for (i = 0; i < 5; i = i + 1)
  continue;
  a = 1;
rof
a;
"""
    ).value,
    0,
)

# scope and functions
assert_or_log(interpret("a = 1; a;").value, 1)
assert_or_log(interpret("a = 1; a = 2; a;").value, 2)
assert_or_log(interpret("fun a() 1; 2; 3; 4; nuf a();").value, None)
assert_or_log(interpret("fun a() 1; 2; return 3; 4; nuf a();").value, 3)
assert_or_log(interpret("fun a() 1; 2; return 3; 0 / 0; nuf a();").value, 3)
assert_or_log(interpret("a = 1; fun alter() a = 2; nuf alter(); a;").value, 2)
assert_or_log(interpret("fun a(b, c) return b * c; nuf -a(3, 4);").value, -12)
assert_or_log(interpret("fun a(b, c) return b * c; nuf a(3, 4) * a(3, 4);").value, 144)
assert_or_log(type(interpret("fun a() 1; nuf a; b = a; b;").value).__name__, "function")
assert_or_log(isinstance(interpret("fun a() 1; nuf"), NilValue), True)
assert_or_log(
    interpret(
        """
fun a()
  fun inner(b)
    return b * b;
  nuf
  return inner;
nuf
a()(3);
"""
    ).value,
    9,
)
assert_or_log(
    interpret(
        """
fun fib(x)
  if (x == 0 or x == 1)
    return x;
  fi
  return fib(x - 1) + fib(x - 2);
nuf
fib(10);
"""
    ).value,
    55.0,
)
assert_or_log(
    isinstance(
        interpret(
            """
fun _()
  return;
nuf
_();
"""
        ),
        NilValue,
    ),
    True,
)
assert_or_log(
    interpret(
        """
j = 0;
fun early_return()
  for (i = 0; i < 5; i = i + 1)
    j = j + 1;
    return;
  rof
nuf
early_return();
j;
"""
    ).value,
    1,
)

# errors
assert_or_log(str(interpret("(0 / 0);")), "1:2 [error] cannot divide by zero")
assert_or_log(
    str(interpret("a = 1; fun alter() b = 2; nuf alter(); b;")),
    "1:40 [error] unknown variable 'b'",
)
assert_or_log(str(interpret("a;")), "1:1 [error] unknown variable 'a'")
assert_or_log(
    str(interpret("b = 7; b();")),
    "1:8 [error] [(NumberValue: 7.0)] only functions are callable",
)
assert_or_log(
    str(interpret("if (1) fi")),
    "1:1 [error] [(NumberValue: 1.0)] if expressions expect a boolean",
)
assert_or_log(
    str(
        interpret(
            """
    a = 1000;
    fun decr()
      a = a - 1;
      decr();
    nuf
    decr();
    """
        )
    ),
    "5:7 [error] maximum recursion depth exceeded",
)
assert_or_log(
    str(interpret("for (i = 0; i < 5; i = i + 1) rof i;")),
    "1:35 [error] unknown variable 'i'",
)
assert_or_log(
    str(interpret("break;")),
    "1:1 [error] can't use 'break' outside of for loop body",
)
assert_or_log(
    str(interpret("continue;")),
    "1:1 [error] can't use 'continue' outside of for loop body",
)
assert_or_log(
    str(interpret("for (i = 0; i < 5; i = i + 1) fun b() break; nuf b(); rof")),
    "1:39 [error] can't use 'break' outside of for loop body",
)
assert_or_log(
    str(interpret("for (i = 0; i < 5; i = i + 1) fun b() continue; nuf b(); rof")),
    "1:39 [error] can't use 'continue' outside of for loop body",
)

print("tests passed!")

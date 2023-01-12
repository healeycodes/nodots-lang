from interpreter import interpret

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

# functions!
fun some_func(b, c)
  return b * c;
nuf
some_func(some_var, 5);

# fibonacci
fun fib(x)
  if (x == 0 or x == 1)
    return x;
  fi
  return fib(x - 1) + fib(x - 2);
nuf
fib(10);

# functions have their own scope!
z = 1;
fun mutate_z()
  z = 2;
  some_local_var = 3;
nuf
mutate_z();
z; # <-- z is now `2`
# some_local_var; <-- would be an error

# closures!
fun closure()
  fun inner()
    return z;
  nuf
  return inner;
nuf
closure()(); # 2
"""


def assert_or_log(a, b):
    try:
        assert a == b
    except AssertionError as e:
        print(f"{a} != {b}")
        print("tests failed!")
        quit(1)


# example programs
assert_or_log(interpret(kitchen_sink_example).value, 2)

# basic types
assert_or_log(interpret("1;").value, 1)
assert_or_log(interpret("1.5;").value, 1.5)
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

# compare
assert_or_log(interpret("1 == 1;").value, True)
assert_or_log(interpret("1 != 1;").value, False)
assert_or_log(interpret("1 >= 1;").value, True)
assert_or_log(interpret("1 <= 1;").value, True)
assert_or_log(interpret("2 < 3;").value, True)
assert_or_log(interpret("3 > 2;").value, True)

# expressions
assert_or_log(interpret("-1;").value, -1)
assert_or_log(interpret("(1);").value, 1)
assert_or_log(interpret("-(1);").value, -1)
assert_or_log(interpret("(1 + 1);").value, 2)
assert_or_log(interpret("(1 - 1);").value, 0)
assert_or_log(interpret("(2 * 2);").value, 4)
assert_or_log(interpret("(2 * 2) * (7 + 8);").value, 60)
assert_or_log(interpret("(1 / 1);").value, 1)
assert_or_log(interpret("a = (6 * 6); a;").value, 36)

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

print("tests passed!")

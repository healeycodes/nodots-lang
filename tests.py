import os
import signal
import subprocess
import time
from interpreter import NilValue, interpret


def rm_file(fp):
    try:
        os.remove(fp)
    except OSError:
        pass


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

# lists!
some_list = list(-1, 3, 4);
at(some_list, 0); # -1
mut(some_list, 0, -2); # as in _mutate_
at(some_list, 0); # -2

# dictionaries!
some_dict = dict("a", 2);
mut(some_dict, "a", "hi!");
at(some_dict, "a"); # "hi!"

# (also)
keys(some_dict);
vals(some_dict);

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

# dicts
assert_or_log(interpret('dict("a", "b");').value["a"].value, "b")
assert_or_log(interpret('dict("1", "b");').value["1"].value, "b")
assert_or_log(
    str(interpret('dict("a");')),
    "1:1 [error] dict expects an even number of args e.g. `k, v, k, v`, got: ['(StringValue: a)']",
)
assert_or_log(
    interpret(
        """
a = dict("_", "b");
mut(a, "_", "c");
at(a, "_");
"""
    ).value,
    "c",
)
assert_or_log(
    interpret(
        """
a = dict();
at(a, "missing");
"""
    ).value,
    None,
)
assert_or_log(
    interpret(
        """
a = dict("b", 2);
keys(a);
"""
    )
    .value[0]
    .value,
    "b",
)
assert_or_log(
    interpret(
        """
a = dict("b", 2);
vals(a);
"""
    )
    .value[0]
    .value,
    2,
)

# lists
assert_or_log(interpret('list("a");').value[0].value, "a")
assert_or_log(
    interpret(
        """
a = list("b");
mut(a, 0, "c");
at(a, 0);
"""
    ).value,
    "c",
)
assert_or_log(
    str(
        interpret(
            """
a = list();
at(a, 1);
"""
        )
    ),
    "3:1 [error] list index out of bounds, len: 0 got: 1.0",
)

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

# builtins
assert_or_log(interpret('join("a", "b");').value, "ab")
assert_or_log(interpret('at(join(list("a"), list("b")), 0);').value, "a")
assert_or_log(interpret('at(join(list("a"), list("b")), 1);').value, "b")

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
assert_or_log(
    str(interpret("read();")),
    "1:1 [error] read() expects two args (string, function), got []",
)
assert_or_log(
    str(interpret("write();")),
    "1:1 [error] write() expects two args (string, string | number), got []",
)

# i/o
assert_or_log(
    str(
        interpret(
            """
                data = nil;
                fun read_function(chunk)
                  # first call: the entire file
                  # second call: an empty string
                  if (chunk != "")
                    data = chunk;
                  fi
                nuf;
                read("./example.txt", read_function);
                data;"""
        ).value
    ),
    "# this file is used for integration tests e.g. read()\n",
)

# write str
write_path_1 = "./_test_write.txt"
data_1 = "1"
rm_file(write_path_1)
assert_or_log(
    interpret(f'write("{write_path_1}", "{data_1}");').value,
    None,
)
with open(write_path_1, "r") as f:
    assert f.read() == data_1
rm_file(write_path_1)

# write num
write_path_2 = "./_test_write.txt"
data = 1
rm_file(write_path_2)
assert_or_log(
    interpret(f'write("{write_path_2}", "{data}");').value,
    None,
)
with open(write_path_2, "r") as f:
    assert f.read() == str(data)
rm_file(write_path_2)

# stdlib
assert_or_log(
    str(
        interpret(
            """
                data = read_all("./example.txt");
                data;
"""
        ).value
    ),
    "# this file is used for integration tests e.g. read()\n",
)

# repl
repl_process = subprocess.Popen(
    ["python3", "./repl.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
)
repl_process.stdin.write(b"1;\n") # type: ignore
repl_process.stdin.flush() # type: ignore
time.sleep(0.1)  # would prefer not to sleep..
repl_process.send_signal(signal.SIGINT)
assert_or_log(repl_process.stdout.read(), b"> 1.0\n> ") # type: ignore
 

print("tests passed!")

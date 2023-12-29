[![Tests](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml/badge.svg)](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml)

# nodots lang
> My blog posts:
> - [Adding For Loops to an Interpreter](https://healeycodes.com/adding-for-loops-to-an-interpreter)
> - [Profiling and Optimizing an Interpreter](https://healeycodes.com/profiling-and-optimizing-an-interpreter)

<br>

A small programming language without any dots called **nodots**. There are two versions of this language; static types and a custom WebAssembly compiler (w/ type checking), and dynamic types with a tree-walk interpreter. Both use [Lark](https://lark-parser.readthedocs.io/en/latest/index.html) for parsing.

<br>

## WebAssembly Compiler (static types)

`compiler.py` is a WebAssembly compiler (w/ type checking) that outputs WebAssembly Text Format. See `grammar_static.py` for the grammar.

This version is more experimental than the interpreter but you can compile and run an example program with:

```text
pip3 install -r requirements.txt
./compile.sh
```

The example program is a naive algorithm that calculates the n-th Fibonacci number. It requires ~67million function calls and runs 4000x quicker in the compiled version.

```text
fn fib(i32 n) -> i32
  if (n == 0)
    return 0;
  fi
  if (n == 1)
    return 1;
  fi
  return fib(n - 1) + fib(n - 2);
nf
```

The binary of this program is 134 bytes when encoded in base64. This is much smaller than: a Python runtime, the Lark parsing library, and a 1k LOC interpreter!

<br>

## Interpreter (dynamic types)

`interpreter.py` is a tree-walk interpreter. See `grammar.py` for the grammar.

Here's an example program (see `tests.py` for more examples).

```python
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
join(list(1), list(2)); # [1, 2]
len(list(1, 2, 3)); # 3

# dictionaries!
some_dict = dict("a", 2, "b", 3); # (k, v, k, v, ...)
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

# i/o!
write("./foo", "bar");
data = read_all("./foo");

fun read_function(chunk)
  log(chunk);
nuf
read("./foo", read_function);
```

### Install

`pip3 install -r requirements.txt`

### Run

`python3 cli.py sourcefile`

### Tests

`./test.sh`

- Mypy type checking
- Tests programs

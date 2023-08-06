[![Tests](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml/badge.svg)](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml)

# nodots lang
> My blog posts:
> - [Adding For Loops to an Interpreter](https://healeycodes.com/adding-for-loops-to-an-interpreter)
> - [Profiling and Optimizing an Interpreter](https://healeycodes.com/profiling-and-optimizing-an-interpreter)

<br>

A small programming language without any dots called **nodots**. I had some trouble with a previous language when it came to mutating via dot access – so I decided: no dots this time (okay, fine, you can use dots for floats).

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

## Install

`pip3 install -r requirements.txt`

## Run

`python3 cli.py sourcefile`

## Tests

`./test.sh`

- Mypy type checking
- Tests programs

## More

It's a tree-walk interpreter implemented in Python, using [Lark](https://lark-parser.readthedocs.io/en/latest/index.html) for parsing.

See `grammar.py` for the [EBNF](https://lark-parser.readthedocs.io/en/latest/grammar.html#general-syntax-and-notes)-ish language grammar.

As linked at the top of this README, I've written two blog posts about this project.

- [Adding For Loops to an Interpreter](https://healeycodes.com/adding-for-loops-to-an-interpreter)
- [Profiling and Optimizing an Interpreter](https://healeycodes.com/profiling-and-optimizing-an-interpreter)

## Project TODOs

Standard functions:
- more file/dir/system functions
- assert()
- type() / casting


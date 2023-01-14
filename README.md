[![Tests](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml/badge.svg)](https://github.com/healeycodes/nodots-lang/actions/workflows/python-app.yml)

# nodots lang

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
  fun inner()
    return z;
  nuf
  return inner;
nuf
closure()(); # 2
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

See `ideas.md` for what might be coming next.

See `grammar.py` for the [EBNF](https://lark-parser.readthedocs.io/en/latest/grammar.html#general-syntax-and-notes)-ish language grammar.

## Project TODOs

Data structures:
- list()
- dict()

Standard functions:
- assert()
- input / output
- type() / casting

Maybe:
- Expand recursive function calls to a flat loop. So that a naive recursive fibonacci function called with `100` doesn't result in a Python `RecursionError` error.


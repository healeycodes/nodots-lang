from interpreter import interpret

program = """
for (i = 0; i < 20; i = i + 1)
  # gets called 35400 times
  fun fib(x)
    if (x == 0 or x == 1)
        return x;
    fi
    return fib(x - 1) + fib(x - 2);
  nuf
  fib(i);
rof
"""

interpret(program, opts={"debug": False, "profile": True})

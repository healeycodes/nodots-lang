import readline
from interpreter import eval_program, get_context, get_root


def repl():
    readline.parse_and_bind('"\e[A": history-search-backward')
    readline.parse_and_bind('"\e[B": history-search-forward')

    lines = []
    prompt = "> "

    root_context = get_context({"debug": False})

    while True:
        try:
            line = input(prompt)
            lines.append(line)
            inner_value = eval_program(get_root(line), context=root_context).value
            print(f"{inner_value if inner_value is not None else 'nil'}")
        except KeyboardInterrupt:
            quit()
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    repl()

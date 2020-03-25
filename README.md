# Quickstart

argcomb (argument combiner) is a simple utility that allows you to build
complex command-line arguments in a modular fashion.

To install it:

    pip install argcomb

Suppose we want to run the following combination of commands (e.g., if you're
doing a hyperparameter sweep):

    echo train --eta 0.1 --num-iters 5 --greedy
    echo train --eta 0.1 --num-iters 5
    echo train --eta 0.1 --num-iters 10 --greedy
    echo train --eta 0.1 --num-iters 10

You can write the following `argcomb` program (called `example1.py` in this repo):

    from argcomb import *

    run(
        "echo", "train",
        arg("eta", 0.1),
        selarg(None, "num-iters", 5, 10),
        sel(None, [], arg("greedy")),
    )

Here `run` takes a (hierarchical) list of arguments to be concatenated.
Special functions like `sel` allow us to specify the selection/iteration over
multiple possible values in place (as opposed to having a big for loop on the
outside).

To run it:

    # Actually executes the commands
    python example1.py

    # Print out the commands rather than execute them
    python example1.py -n

We can also use environment variables (e.g., `@mode`) to parametrize the runs.
For example:

    from argcomb import *

    run(
        "echo", "train",
        let_if_undefined("@mode", "slow"),  # Set default
        sel("@mode", {
            "fast": [arg("num-iters", 5), arg("greedy")],
            "slow": arg("num-iters", 10),
        }),
        arg("output", fmt("@mode.out")),
    )

To run it:

    python example.py             # slow (default)
    python example.py @mode=fast  # fast

# Development

Handy commands:

    # Install environment
    virtualenv -p python3.7 venv
    venv/bin/pip install -r requirements.txt

    # Format code (skip `example*.py`)
    venv/bin/black -t py37 argcomb test_argcomb.py

    # Do type checking
    venv/bin/python -m mypy argcomb test_argcomb.py example*.py

    # Run unit tests
    venv/bin/python -m pytest test_argcomb.py

    # Build PyPI package and deploy it
    venv/bin/python setup.py sdist
    venv/bin/twine upload dist/*

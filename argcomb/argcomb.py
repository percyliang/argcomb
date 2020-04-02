import os
import re
import shlex
import json
import sys
from collections import namedtuple, OrderedDict
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

Arg = namedtuple("Arg", "name values append delete")
Selector = namedtuple("Selector", "which choices")
Let = namedtuple("Let", "var value if_undefined")

# List and Callable are not parametrized because mypy doesn't support recursive types
Expr = Optional[Union[bool, int, float, str, List, Arg, Selector, Let, Callable]]
Env = Dict[str, Any]
EnvExpr = Callable[[Env], Expr]
Choices = Union[List[Expr], Dict[str, Expr]]


class ArgcombException(Exception):
    """For user errors."""

    def __init__(self, message):
        self.message = message


############################################################
# Helper functions


def parse_value(value: str) -> Expr:
    """Try to interpret the value as JSON, else fallback to string."""
    try:
        return json.loads(value)
    except ValueError:
        return value


def lookup_env(env: Env, key: str) -> Expr:
    """Return `env[key]` or print an error if it doesn't exist."""
    if key not in env:
        raise ArgcombException(f"{key} not in {env}")
    return env[key]


############################################################
# Main class


class ArgCombiner(object):
    def __init__(self, args: List[str] = sys.argv[1:], pretend: bool = False):
        # - Initial environment variables: @<var>=<value>
        # - Pretend flag: -n
        self.extra_args = []  # args without the ArgCombiner flags
        self.init_env: Env = {}
        for arg in args:
            if arg == "-n":  # Similar to what `make -n` does
                pretend = True
                continue
            m = re.fullmatch(r"(@\w+)=(.*)$", arg)
            if m:
                var, value = m.group(1), m.group(2)
                self.init_env[var] = parse_value(value)
                continue
            self.extra_args.append(arg)

        self.pretend = pretend

    def execute(self, expr: Expr, env: Env) -> Iterator[Tuple[Expr, Env]]:
        if not isinstance(expr, list):
            raise ArgcombException(f"Expect a list, but got: {expr}")
        return self.internal_execute(expr + self.extra_args, env)

    def execute_list(self, expr: List[Expr], env: Env) -> Iterator[Tuple[Expr, Env]]:
        """Take the cross-product of executing all the elements of `expr`."""
        if len(expr) == 0:
            yield (expr, env)
        else:
            first, rest = expr[0], expr[1:]
            for new_first, new_first_env in self.internal_execute(first, env):
                for new_rest, new_rest_env in self.internal_execute(
                    rest, new_first_env
                ):
                    if not isinstance(new_rest, list):
                        raise ValueError(
                            f"Internal error: execute on list {rest} should return list, but got {new_rest}"
                        )
                    yield ([new_first] + new_rest, new_rest_env)

    def internal_execute(self, expr: Expr, env: Env) -> Iterator[Tuple[Expr, Env]]:
        """
        Main functionality for executing `expr` against an environment `env`.
        Generates a list of (`new_expr`, `new_env`) candidates.
        We expand out based on selectors and resolve environment variables.
        """
        if isinstance(expr, list):
            for new_expr, new_env in self.execute_list(expr, env):
                yield (new_expr, new_env)

        elif isinstance(expr, Arg):
            # Execute the values inside `Arg`
            for new_values, new_env in self.execute_list(expr.values, env):
                yield (expr._replace(values=new_values), new_env)

        elif isinstance(expr, Selector):
            # Canonicalize to dict representation for `choices`
            if isinstance(expr.choices, list):
                # Map from index (0, 1, 2, ...) to elements of the list
                choices = dict(zip(range(len(expr.choices)), expr.choices))
            elif isinstance(expr.choices, dict):
                choices = expr.choices
            else:
                raise ArgcombException(f"Expected list or dict, but got {expr.choices}")

            # Lookup variable in environment
            if isinstance(expr.which, str) and expr.which.startswith("@"):
                which = lookup_env(env, expr.which)
            else:
                which = expr.which

            # Canonicalize to list for `which`
            if which is None:
                which = list(choices.keys())  # Select all of them
            elif isinstance(which, list):
                pass
            else:
                which = [which]

            for key in which:
                if key not in choices:
                    raise ArgcombException(f"{key} not in {list(choices.keys())}")
                for new_expr, new_env in self.internal_execute(choices[key], env):
                    yield (new_expr, new_env)

        elif isinstance(expr, Let):
            # Update the environment
            if not expr.if_undefined or expr.var not in env:
                # `if_undefined` => only update the environment if we haven't defined it yet
                for new_value, new_env in self.internal_execute(expr.value, env):
                    yield (expr, dict(list(new_env.items()) + [(expr.var, new_value)]))
            else:
                yield (expr, env)

        elif callable(expr):
            # Call `expr` on the environment
            for new_expr, new_env in self.internal_execute(expr(env), env):
                yield (new_expr, new_env)

        else:
            # A primtive value (e.g., a string), just leave as is.
            yield (expr, env)

    def flatten(self, expr: Expr) -> List[Expr]:
        """Return a flat list containing elements of `expr`."""
        if isinstance(expr, list):
            return [y for x in expr for y in self.flatten(x)]
        else:
            return [expr]

    def interpret_args(self, exprs: List[Expr]) -> List[Expr]:
        """
        Given a flattened list `exprs`, handle all `Arg` instances in `exprs`.
        This complexity is really due to the fact that we support append arguments.
        """
        arg_values: OrderedDict[str, List[Expr]] = OrderedDict()  # name -> values
        for expr in exprs:
            if isinstance(expr, Arg):
                if expr.name not in arg_values:
                    arg_values[expr.name] = []
                if expr.append:
                    arg_values[expr.name].extend(expr.values)
                elif expr.delete:
                    del arg_values[expr.name]
                else:  # Just set normally
                    arg_values[expr.name] = list(expr.values)

        new_exprs = []
        for expr in exprs:
            if isinstance(expr, Arg):
                # Only interpret the first occurrence of the argument (subsequent ones are just modifications)
                # Note that an argument doesn't get added if it has been deleted
                if expr.name in arg_values:
                    new_exprs.append("--" + expr.name)
                    new_exprs.extend(arg_values[expr.name])
                    del arg_values[expr.name]
            elif isinstance(expr, Let):
                pass
            else:
                new_exprs.append(expr)

        return new_exprs

    def to_command(self, expr: Expr) -> str:
        """Internal command that converts `expr` into a string."""
        tokens = self.interpret_args(self.flatten(expr))
        str_tokens = list(map(str, tokens))
        command = " ".join(map(shlex.quote, str_tokens))
        return command

    def run(self, expr: Expr) -> None:
        """Main entry point.  Execute and then convert into a command."""
        try:
            for new_expr, new_env in self.execute(expr, self.init_env):
                command = self.to_command(new_expr)
                if self.pretend:
                    print(command)
                else:
                    raw_exitcode = os.system(command)
                    # See https://stackoverflow.com/questions/55014222/what-are-response-codes-for-256-and-512-for-os-system-in-python-scripting
                    exitcode = raw_exitcode >> 8
                    if exitcode != 0:
                        sys.exit(exitcode)
        except ArgcombException as e:
            print(e.message, file=sys.stderr)
            sys.exit(1)


def standardize_choices(choices, transform: Callable[[Expr], Expr]) -> Choices:
    """Helper function for `sel` and `selarg`."""
    if len(choices) == 1 and isinstance(choices[0], dict):
        return choices[0]
    return list(map(transform, choices))


############################################################
# Functions that will be used externally.


def run(*expr) -> None:
    """Main entry point."""
    ArgCombiner().run(list(expr))


def arg(name: str, *values, **kwargs) -> Arg:
    """Represents an argument --`name` `values` which some special features for
    modifying previous instances of --`name`."""
    return Arg(
        name=name,
        values=list(values),
        append=kwargs.get("append", False),
        delete=kwargs.get("delete", False),
    )


def sel(which: Expr, *choices) -> Selector:
    """Selects among `choices` based on `which`."""
    return Selector(
        which=which, choices=standardize_choices(choices, lambda choice: choice)
    )


def selarg(which: Expr, name: str, *choices) -> Selector:
    """Sugar for selector over arguments."""
    return Selector(
        which=which,
        choices=standardize_choices(choices, lambda choice: arg(name, choice)),
    )


def let(var: str, value: Expr, if_undefined: bool = False) -> Let:
    """Update the environment with `var`: `value`."""
    return Let(var=var, value=value, if_undefined=if_undefined)


def let_if_undefined(var: str, value: Expr) -> Let:
    return let(var, value, if_undefined=True)


def fmt(string: str) -> EnvExpr:
    """Replace all environment variable references in `string` with an environment lookup."""
    return lambda env: re.sub(
        r"@\w+", lambda m: str(lookup_env(env, m.group())), string
    )


def split(string: str) -> List[str]:
    """
    Split string (which represents a command) into a list.
    This allows us to just copy/paste command prefixes without having to define a full list.
    """
    return shlex.split(string)

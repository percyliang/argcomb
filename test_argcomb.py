from argcomb import *
from argcomb.argcomb import ArgCombiner, Expr
from typing import List


def check(expr: List[Expr], true_commands: List[str], args: List[str] = []):
    """Execute `expr` with `args` and ensure that you get `true_commands`."""
    combiner = ArgCombiner(args)
    pred_commands = []
    for new_expr, new_env in combiner.execute(expr, {}):
        pred_commands.append(combiner.to_command(new_expr))
    assert true_commands == pred_commands


def test_basic():
    check(["echo", "hello"], ["echo hello"])
    check(["echo", "hello world"], ["echo 'hello world'"])  # Quote spaces
    check(["echo", ""], ["echo ''"])  # Empty
    check(["echo", 1, 3.14], ["echo 1 3.14"])  # Non-string types
    check(["echo", ["hello", ["world"]]], ["echo hello world"])  # Flatten


def test_arg():
    check(["foo", arg("bar")], ["foo --bar"])
    check(["foo", arg("bar", 3)], ["foo --bar 3"])
    check(["foo", arg("bar", 3), arg("bar", 5)], ["foo --bar 5"])  # Replace
    check(
        ["foo", arg("bar", 3), arg("bar", 5, append=True)], ["foo --bar 3 5"]
    )  # Append
    check(["foo", arg("bar", 3), arg("bar", delete=True)], ["foo"])  # Delete


def test_sel():
    # List
    check(["foo", sel(0, "bar", "baz")], ["foo bar"])
    check(["foo", sel(1, "bar", "baz")], ["foo baz"])
    check(["foo", sel(None, "bar", "baz")], ["foo bar", "foo baz"])
    check(["foo", sel([0, 1], "bar", "baz")], ["foo bar", "foo baz"])
    # Dict
    check(["foo", sel("a", {"a": "bar", "b": "baz"})], ["foo bar"])
    check(["foo", sel(["a", "b"], {"a": "bar", "b": "baz"})], ["foo bar", "foo baz"])
    # selarg
    check(["foo", selarg(None, "name", "a1", "a2")], ["foo --name a1", "foo --name a2"])


def test_let():
    check(["foo", let("@x", 3), lambda env: env["@x"]], ["foo 3"])
    check(["foo", let("@x", 3), fmt("iter=@x")], ["foo iter=3"])
    # Test if_undefined
    check(["foo", let("@x", 3), let("@x", 4), fmt("iter=@x")], ["foo iter=4"])
    check(
        ["foo", let("@x", 3), let("@x", 4, if_undefined=True), fmt("iter=@x")],
        ["foo iter=3"],
    )


def test_recurse():
    # Check that execution happens recursively
    check(["foo", let("@x", 3), fmt("iter=@x")], ["foo iter=3"])  # List
    check(
        ["foo", let("@x", 3), arg("bar", fmt("iter=@x"))], ["foo --bar iter=3"]
    )  # Arg
    check(["foo", let("@x", 3), sel(0, fmt("iter=@x"))], ["foo iter=3"])  # Selector
    check(
        ["foo", let("@x", 3), let("@y", fmt("@x")), fmt("iter=@y")], ["foo iter=3"]
    )  # Let
    check(["foo", let("@x", 3), lambda env: fmt("iter=@x")], ["foo iter=3"])  # Callable


def test_split():
    check(["echo", split('foo bar "baz"')], ["echo foo bar baz"])


def test_constructor():
    check(["echo", "hello"], ["echo hello world"], args=["world"])  # Extra arguments


def test_end_to_end():
    run(["echo", "hello"])  # Just make sure this doesn't crash


test_constructor()

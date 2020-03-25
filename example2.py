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

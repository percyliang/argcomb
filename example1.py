from argcomb import *

run(
    "echo", "train",
    arg("eta", 0.1),
    selarg(None, "num-iters", 5, 10),
    sel(None, [], arg("greedy")),
)

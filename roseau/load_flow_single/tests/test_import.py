import roseau.load_flow as rlf
import roseau.load_flow_single as rlfs


def test_import():
    # Ensure that RLF and RLFS have nearly the same interface
    rlf_dir = set(dir(rlf)) - {"ConductorType", "InsulatorType"}
    rlfs_dir = set(dir(rlfs))

    assert rlf_dir - rlfs_dir == {
        # Multi-phase elements
        "Ground",
        "PotentialRef",
        # Sequences
        "NegativeSequence",
        "PositiveSequence",
        "ZeroSequence",
        "ALPHA",
        "ALPHA2",
        "converters",
        # Plotting
        "plotting",
        # Symmetrical components
        "sym",
        # Underscore things
        "__getattr__",
        "__about__",
        "_compat",
        "_solvers",
        # Unrelated imports
        "Any",
        "importlib",
    }
    # conftest is not included in wheels
    assert rlfs_dir - rlf_dir <= {"conftest"}

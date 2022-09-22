from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode


def test_exceptions():
    for x in RoseauLoadFlowExceptionCode:
        # String starts with the package name
        assert str(x).startswith("roseau.load_flow.")

        # String equality
        assert str(x) == x

        # No equality without the prefix
        assert str(x).removeprefix("roseau.load_flow.") != x

        # Case-insensitive
        assert str(x).upper() == x

    r = RoseauLoadFlowException(msg="toto", code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
    assert r.msg == "toto"
    assert isinstance(r.code, RoseauLoadFlowExceptionCode)
    assert r.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
    assert r.args[0] == "toto"
    assert isinstance(r.args[1], RoseauLoadFlowExceptionCode)
    assert r.args[1] == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

from roseau.load_flow.exceptions import RoseauLoadFlowException, RoseauLoadFlowExceptionCode


def test_exceptions():
    for x in RoseauLoadFlowExceptionCode:
        # Case-insensitive
        assert str(x).upper() == x
        assert str(x).lower() == x
    # Case-insensitive constructor (with or without spaces or dashes)
    # spellchecker:off
    assert RoseauLoadFlowExceptionCode("BaD_bus_ID") == RoseauLoadFlowExceptionCode.BAD_BUS_ID
    assert RoseauLoadFlowExceptionCode("bad bus id") == RoseauLoadFlowExceptionCode.BAD_BUS_ID
    assert RoseauLoadFlowExceptionCode("BAD-BUS-ID") == RoseauLoadFlowExceptionCode.BAD_BUS_ID
    # spellchecker:on
    r = RoseauLoadFlowException(msg="toto", code=RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS)
    assert r.msg == "toto"
    assert isinstance(r.code, RoseauLoadFlowExceptionCode)
    assert r.code == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS
    assert r.args[0] == "toto"
    assert isinstance(r.args[1], RoseauLoadFlowExceptionCode)
    assert r.args[1] == RoseauLoadFlowExceptionCode.BAD_TRANSFORMER_WINDINGS

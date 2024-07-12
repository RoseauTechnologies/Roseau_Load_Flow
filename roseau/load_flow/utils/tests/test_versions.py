import re

from roseau.load_flow import show_versions
from roseau.load_flow.utils._versions import _get_dependency_info, _get_sys_info


def test_versions(capsys):
    show_versions()
    captured = capsys.readouterr()
    assert captured.err == ""
    lines = captured.out.split("\n")
    assert lines[1] == "System Information"
    assert lines[2] == "------------------"
    for i, (key, value) in enumerate(_get_sys_info().items()):
        assert re.fullmatch(pattern=rf"{key}\s+{value}", string=lines[3 + i])
    assert lines[7] == ""
    assert lines[8] == "Installed Dependencies"
    assert lines[9] == "----------------------"
    for i, (key, value) in enumerate(_get_dependency_info().items()):
        assert re.fullmatch(pattern=rf"{key}\s+{value}", string=lines[10 + i])
    assert lines[20] == ""

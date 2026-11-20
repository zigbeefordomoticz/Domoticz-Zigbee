"""
tests/Classes/Groups/test_group_error_codes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The logging rules of Group Management, checked on the source:

- every Error passes a context, with a code declared in GRP_ERROR_CODES;
- the codes are "GRP" + 4 digits, each declared once and used once;
- a log line of a function that receives a group passes an id, so that
  MatchingNwkId can filter on the group.

The functions under test are taken from the source and run on their own: importing
the real modules here would break unrelated tests through the conftest stubs.

Run with:
    python -m pytest tests/Classes/Groups/test_group_error_codes.py -v
"""

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
GROUP_SOURCES = sorted((ROOT / "Classes" / "GroupMgtv2").glob("*.py"))
REGISTRY = ROOT / "Classes" / "GroupMgtv2" / "GrpErrorCodes.py"
LOGGING_SOURCE = ROOT / "Classes" / "LoggingManagement.py"
CODE_IN_SOURCE = re.compile(r'"Error code":\s*"(GRP\d{4})"')
GROUP_PARAMETERS = {"GroupId", "GrpId", "goup_addr", "group_id"}


def group_error_codes():
    namespace = {}
    exec(REGISTRY.read_text(), namespace)
    return namespace["GRP_ERROR_CODES"]


def function_source(path, name):
    """The function alone, as its module would define it."""
    source = path.read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(source, node, padded=True)
    raise AssertionError(f"{name} not found in {path}")


def group_function(path, name, **namespace):
    # A method is indented: dedent through a class, then take it from there
    exec("class Holder:\n" + function_source(path, name), namespace)
    return getattr(namespace["Holder"], name)


def source_of(*names):
    return "\n\n".join(function_source(ROOT / "Classes" / "GroupMgtv2" / "GrpDomoticz.py", name) for name in names)


def logging_calls(tree):
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "logging"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "self"
            ):
                yield function, node


class TestErrorCodes:

    def test_codes_are_well_formed_and_described(self):
        for code, description in group_error_codes().items():
            assert re.fullmatch(r"GRP\d{4}", code), code
            assert description

    def test_codes_are_declared_once(self):
        declared = re.findall(r'^\s*"(GRP\d{4})":', REGISTRY.read_text(), re.MULTILINE)

        assert len(declared) == len(set(declared))

    def test_every_code_is_used_once_and_declared(self):
        used = [code for path in GROUP_SOURCES if path != REGISTRY for code in CODE_IN_SOURCE.findall(path.read_text())]

        assert used, "no error code found: the pattern no longer matches the source"
        assert sorted(used) == sorted(group_error_codes())

    @pytest.mark.parametrize("path", GROUP_SOURCES, ids=lambda path: path.name)
    def test_every_error_passes_a_coded_context(self, path):
        missing = [
            node.lineno
            for _, node in logging_calls(ast.parse(path.read_text()))
            if isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "Error"
            and not (
                len(node.args) == 4
                and isinstance(node.args[3], ast.Dict)
                and any(isinstance(key, ast.Constant) and key.value == "Error code" for key in node.args[3].keys)
            )
        ]

        assert missing == []


class TestGroupIdInLogs:

    @pytest.mark.parametrize("path", GROUP_SOURCES, ids=lambda path: path.name)
    def test_a_function_about_a_group_passes_an_id(self, path):
        missing = [
            (function.name, node.lineno)
            for function, node in logging_calls(ast.parse(path.read_text()))
            if {arg.arg for arg in function.args.args} & GROUP_PARAMETERS and len(node.args) < 3
        ]

        assert missing == []


class TestLoggingWrapper:

    @pytest.fixture
    def manager(self):
        method = group_function(ROOT / "Classes" / "GroupMgtv2" / "GroupManagement.py", "logging")
        fake = MagicMock()
        fake.logging = lambda *args, **kwargs: method(fake, *args, **kwargs)
        return fake

    def test_id_and_context_reach_the_logger(self, manager):
        manager.logging("Error", "message", "0002", {"Error code": "GRP0101"})

        manager.log.logging.assert_called_once_with("Groups", "Error", "message", "0002", {"Error code": "GRP0101"})

    def test_they_stay_optional(self, manager):
        manager.logging("Status", "message")

        manager.log.logging.assert_called_once_with("Groups", "Status", "message", None, None)

    def test_an_empty_id_is_no_id(self, manager):
        # The debug filter silently drops a line with an empty id
        manager.logging("Debug", "message", "")

        manager.log.logging.assert_called_once_with("Groups", "Debug", "message", None, None)


class TestMatchingNwkId:
    """The debug filter, as it receives the id: enqueue_logging has made it a string."""

    @pytest.fixture
    def shown(self):
        return []

    def filtered(self, shown, matching, nwkid):
        namespace = {"_logging_to_plugin_log": lambda *args: shown.append(args[-1])}
        exec(function_source(LOGGING_SOURCE, "_debug_logging_filtering"), namespace)
        fake = MagicMock()
        fake.pluginconf.pluginConf = {"MatchingNwkId": matching}
        namespace["_debug_logging_filtering"](fake, "thread", "message", "Groups", nwkid)
        return shown

    @pytest.mark.parametrize("matching", ["0002", "8c11,0002", "ffff", "0002 "])
    def test_a_group_id_passes(self, shown, matching):
        assert self.filtered(shown, matching, "0002") == ["0002"]

    def test_another_group_does_not(self, shown):
        assert self.filtered(shown, "0003", "0002") == []

    def test_a_line_without_an_id_only_passes_with_ffff(self, shown):
        # What every Group Management debug line did: filtering on a device hid them all
        assert self.filtered(shown, "8c11", "None") == []
        assert self.filtered(shown, "ffff", "None") == ["none"]


class TestMissingMember:
    """update_device_list_attribute, whose Error used to log the id it had just lost."""

    GROUP = "0002"
    IEEE = "0017880102a3b4c5"

    @pytest.fixture
    def manager(self):
        fake = MagicMock()
        fake.ListOfGroups = {self.GROUP: {"Devices": [["8c11", "0b", self.IEEE]]}}
        fake.ListOfDevices = {}
        fake.IEEE2NWK = {}
        return fake

    def update(self, manager):
        namespace = {"update_due_to_nwk_id_change": MagicMock()}
        exec(source_of("check_and_fix_missing_device", "update_device_list_attribute"), namespace)
        namespace["update_device_list_attribute"](manager, self.GROUP, "0006", "01")

    def test_error_names_the_device_it_could_not_find(self, manager):
        self.update(manager)

        args = manager.logging.call_args.args
        assert args[0] == "Error"
        assert "Device: 8c11 of Group: 0002" in args[1]
        assert args[2] == self.GROUP
        assert args[3] == {"Error code": "GRP0104", "GroupId": self.GROUP, "NwkId": "8c11", "Ep": "0b", "Ieee": self.IEEE}

    def test_a_new_address_is_followed(self, manager):
        manager.IEEE2NWK = {self.IEEE: "1234"}
        manager.ListOfDevices = {"1234": {"Ep": {"0b": {"ClusterType": {}, "0006": {}}}}}

        self.update(manager)

        assert manager.ListOfDevices["1234"]["Ep"]["0b"]["0006"]["0000"] == "01"

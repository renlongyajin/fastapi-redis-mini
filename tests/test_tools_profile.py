import shlex

import pytest

from tools.profile import ProfileConfig, build_profile_command, parse_cli_args


def test_build_cprofile_command_for_callable():
    config = ProfileConfig(
        backend="cprofile",
        module="worker.runner",
        callable_name="main",
        output="worker.prof",
    )
    command = build_profile_command(config)

    assert command[:5] == ["python", "-m", "cProfile", "-o", "worker.prof"]
    assert command[5] == "-c"
    assert command[6] == "from worker.runner import main; main()"


def test_build_pyspy_command_for_module_execution():
    config = ProfileConfig(
        backend="py-spy",
        module="worker.runner",
        callable_name=None,
        output="trace.svg",
        script_args=["--foo", "bar"],
    )
    command = build_profile_command(config)

    assert command[:5] == ["py-spy", "record", "-o", "trace.svg", "--"]
    assert command[5:] == ["python", "-m", "worker.runner", "--foo", "bar"]


@pytest.mark.parametrize(
    "argv,expected_backend,expected_script_args",
    [
            (
                shlex.split("--module worker.runner --backend cprofile"),
                "cprofile",
                [],
            ),
            (
                shlex.split(
                    "--module worker.runner --backend py-spy "
                    "--script-arg=--foo --script-arg=bar --output trace.svg"
                ),
                "py-spy",
                ["--foo", "bar"],
            ),
    ],
)
def test_parse_cli_args(argv, expected_backend, expected_script_args):
    config = parse_cli_args(argv)

    assert config.backend == expected_backend
    assert config.module == "worker.runner"
    assert config.script_args == expected_script_args

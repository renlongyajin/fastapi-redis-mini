from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass, field
from typing import Literal, Sequence

Backend = Literal["cprofile", "py-spy"]


@dataclass
class ProfileConfig:
    module: str
    callable_name: str | None = None
    backend: Backend = "cprofile"
    output: str = "profile.prof"
    script_args: list[str] = field(default_factory=list)


def _callable_snippet(module: str, callable_name: str) -> str:
    return f"from {module} import {callable_name}; {callable_name}()"


def build_profile_command(config: ProfileConfig) -> list[str]:
    if config.backend == "cprofile":
        base = ["python", "-m", "cProfile", "-o", config.output]
        if config.callable_name:
            base.extend(["-c", _callable_snippet(config.module, config.callable_name)])
        else:
            base.extend(["-m", config.module, *config.script_args])
        return base

    if config.backend == "py-spy":
        recorded = ["py-spy", "record", "-o", config.output, "--"]
        if config.callable_name:
            recorded.extend(
                ["python", "-c", _callable_snippet(config.module, config.callable_name)]
            )
        else:
            recorded.extend(["python", "-m", config.module, *config.script_args])
        return recorded

    raise ValueError(f"Unsupported backend: {config.backend}")


def parse_cli_args(argv: Sequence[str] | None = None) -> ProfileConfig:
    parser = argparse.ArgumentParser(description="Run profiling for a module/function.")
    parser.add_argument(
        "--module",
        required=True,
        help="Python module path to profile (e.g. worker.runner)",
    )
    parser.add_argument(
        "--callable",
        dest="callable_name",
        help="Optional callable name inside the module to invoke",
    )
    parser.add_argument(
        "--backend",
        choices=["cprofile", "py-spy"],
        default="cprofile",
        help="Profiling backend to use",
    )
    parser.add_argument(
        "--output",
        default="profile.prof",
        help="Output file path (.prof or .svg)",
    )
    parser.add_argument(
        "--script-arg",
        action="append",
        dest="script_args",
        default=[],
        help="Additional arguments passed to the target module",
    )
    args = parser.parse_args(argv)
    return ProfileConfig(
        module=args.module,
        callable_name=args.callable_name,
        backend=args.backend,  # type: ignore[arg-type]
        output=args.output,
        script_args=args.script_args,
    )


def main(argv: Sequence[str] | None = None) -> None:
    config = parse_cli_args(argv)
    command = build_profile_command(config)
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()

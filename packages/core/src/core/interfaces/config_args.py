# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Load service CLI defaults without bypassing argparse's validation."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

import yaml
from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException

from core.utils.multistorage import MSCStorage


def read_config(path: str) -> dict[str, Any]:
    """Read a local or MSC JSON/YAML mapping; never execute configuration content."""
    with tempfile.TemporaryDirectory(prefix="service_config_") as directory:
        storage = MSCStorage()
        if not storage.is_remote_storage_url(path):
            path = str(Path(path).expanduser())
        local = storage.download_if_remote(path, str(Path(directory) / "config"), is_file=True)
        value = yaml.safe_load(Path(local).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Service configuration must be a JSON/YAML object with string keys.")
    return value


def override_config(config: dict[str, Any], assignments: Sequence[str]) -> dict[str, Any]:
    """Apply dotted KEY=VALUE assignments; JSON values retain their types."""
    try:
        result = OmegaConf.create(config)
        for assignment in assignments:
            key, separator, raw = assignment.partition("=")
            parts = key.split(".")
            if not separator or not all(parts):
                raise ValueError("--set requires a nonempty KEY=VALUE (nested keys use dots).")
            # Keep the public JSON-or-literal contract (e.g. yes and 001 are strings).
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw
            # Inspect unresolved data so a section cannot redirect an override via ${...}.
            parent = cast(dict[str, Any], OmegaConf.to_container(result, resolve=False))
            for part in parts[:-1]:
                child = parent.get(part)
                if child is None:
                    break
                if not isinstance(child, dict):
                    raise ValueError(f"Cannot override nested field beneath {part!r}.")
                parent = child
            OmegaConf.update(result, key, value, merge=False)
        # Prompts and other strings are data, not interpolation expressions.
        return cast(dict[str, Any], OmegaConf.to_container(result, resolve=False))
    except OmegaConfBaseException as exc:
        raise ValueError(f"Invalid configuration override: {exc}") from exc


class ServiceArgumentParser(argparse.ArgumentParser):
    """Parse file defaults through the same actions as explicit CLI arguments."""

    native_config: bool = False

    def configure(self, *, native_config: bool = False) -> None:
        """Add shared config options and negative forms for one-way boolean flags."""
        self.native_config = native_config
        if "--config-file" not in self._option_string_actions:
            self.add_argument(
                "--config-file", help="JSON/YAML service settings; CLI flags override."
            )
        if "--set" not in self._option_string_actions:
            self.add_argument(
                "--set",
                dest="config_overrides",
                action="append",
                default=[],
                metavar="KEY=VALUE",
                help="Override a setting; use JSON for lists/objects.",
            )
        for action in list(self._actions):
            if isinstance(action, argparse._StoreTrueAction):
                option = next((o for o in action.option_strings if o.startswith("--")), None)
                if option and "--no-" + option[2:] not in self._option_string_actions:
                    self.add_argument(
                        "--no-" + option[2:],
                        dest=action.dest,
                        action="store_false",
                        default=argparse.SUPPRESS,
                        help=f"Disable {option}.",
                    )

    def parse_known_args(
        self,
        args: Iterable[str] | None = None,
        namespace: Any = None,
    ) -> tuple[Any, list[str]]:
        """Prepend validated file options, replacing lists when explicitly overridden."""
        argv = list(sys.argv[1:] if args is None else args)
        if "--help" in argv or "-h" in argv:
            return super().parse_known_args(argv, namespace)
        bootstrap = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
        bootstrap.add_argument("--config-file")
        bootstrap.add_argument("--set", dest="config_overrides", action="append", default=[])
        options, _ = bootstrap.parse_known_args(argv)
        try:
            loaded = read_config(options.config_file) if options.config_file else {}
            # Reasoning/PAS retain their task schemas; wrapper CLI settings live under cli.
            config = loaded.get("cli", {}) if self.native_config else loaded
            if not isinstance(config, dict) or not all(isinstance(key, str) for key in config):
                raise ValueError("The cli section must be an object with string keys.")
            canonical = {self._setting_name(key): value for key, value in config.items()}
            if len(canonical) != len(config):
                raise ValueError("Duplicate service setting aliases in configuration.")
            config = canonical
            if not self.native_config:
                assignments = []
                for assignment in options.config_overrides:
                    key, separator, value = assignment.partition("=")
                    assignments.append(self._setting_name(key) + separator + value)
                config = override_config(config, assignments)
            prefix = self._config_tokens(config, argv)
        except (ValueError, OSError, yaml.YAMLError) as exc:
            self.error(str(exc))
        parsed, unknown = super().parse_known_args(prefix + argv, namespace)
        parsed.config_snapshot = loaded if options.config_file else None
        parsed.explicit_cli = {
            self._option_string_actions[token.split("=", 1)[0]].dest
            for token in argv
            if token.split("=", 1)[0] in self._option_string_actions
        }
        parsed.supplied_cli_options = {
            option
            for action in self._actions
            if action.dest in parsed.explicit_cli or action.dest in config
            for option in action.option_strings
        }
        return parsed, unknown

    def _setting_name(self, key: str) -> str:
        """Resolve both CLI spellings and argparse destination names."""
        action = self._option_string_actions.get("--" + key.replace("_", "-"))
        return action.dest if action is not None else key.replace("-", "_")

    def _config_tokens(self, config: dict[str, Any], argv: list[str]) -> list[str]:
        """Translate known settings to CLI tokens, honoring explicit replacements."""
        actions = {
            a.dest: a
            for a in self._actions
            if a.option_strings
            and not isinstance(a, (argparse._HelpAction, argparse._StoreFalseAction))
        }
        explicit = {
            self._option_string_actions[token.split("=", 1)[0]].dest
            for token in argv
            if token.split("=", 1)[0] in self._option_string_actions
        }
        for group in self._mutually_exclusive_groups:
            if any(a.dest in explicit for a in group._group_actions):
                explicit.update(a.dest for a in group._group_actions)
        tokens: list[str] = []
        seen: set[str] = set()
        for key, value in config.items():
            dest = self._setting_name(key)
            if dest in seen:
                raise ValueError(f"Duplicate configuration key: {key}")
            seen.add(dest)
            if dest not in actions or dest in {"config_file", "config_overrides"}:
                raise ValueError(f"Unknown service setting: {key}")
            if dest in explicit:
                continue
            action = actions[dest]
            if value is None:
                if action.default is not None:
                    raise ValueError(f"{key} does not accept null.")
                continue
            flag = next(o for o in action.option_strings if o.startswith("--"))
            if isinstance(action, (argparse._StoreTrueAction, argparse.BooleanOptionalAction)):
                if not isinstance(value, bool):
                    raise ValueError(f"{key} requires a boolean.")
                tokens.append(flag if value else "--no-" + flag[2:])
            elif isinstance(action, argparse._AppendAction):
                if not isinstance(value, list):
                    raise ValueError(f"{key} requires a list.")
                for item in value:
                    tokens.append(f"{flag}={self._text(item)}")
            elif action.nargs in ("+", "*") or isinstance(action.nargs, int):
                if not isinstance(value, list):
                    raise ValueError(f"{key} requires a list.")
                rendered = [self._text(item) for item in value]
                if any(self._parse_optional(item) is not None for item in rendered):
                    raise ValueError(f"{key}: list values cannot be CLI options.")
                tokens.extend([flag, *rendered])
            else:
                tokens.append(f"{flag}={self._text(value)}")
        return tokens

    @staticmethod
    def _text(value: Any) -> str:
        """Serialize structured CLI payloads, including the common input JSON."""
        return value if isinstance(value, str) else json.dumps(value)

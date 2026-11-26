# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import logging
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import yaml
from core import DataEntry
from core.interfaces import ServiceInterface
from core.interfaces.config_args import override_config, read_config
from core.pipelines import LinearPipeline
from core.policy import EmptyOutputPolicy
from core.utils.multistorage import MSCStorage
from daft_validation import DaftValidationTask
from reasoning.config import DaftExportConfig
from reasoning.endpoint_resolver import EndpointResolver
from reasoning.task import ReasoningTask


class ReasoningService(ServiceInterface):
    native_config = True

    def __init__(self) -> None:
        super().__init__(
            name="reasoning_service",
            description="Run opt-in LLM reasoning stages over existing DAFT scene directories.",
        )

    def add_service_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--config-file",
            type=str,
            default=None,
            help="Optional JSON/YAML file containing a reasoning config block.",
        )
        parser.add_argument(
            "--llm-provider",
            choices=("openai-compatible",),
            default="openai-compatible",
            help="Provider adapter for reasoning LLM requests.",
        )
        parser.add_argument(
            "--llm-endpoint-url",
            type=str,
            default="",
            help=(
                "Optional LLM endpoint URL override for opt-in LLM stages. "
                "OpenAI-compatible endpoints accept a /v1 base or a /chat/completions URL."
            ),
        )
        parser.add_argument(
            "--llm-model",
            type=str,
            default="",
            help="Optional LLM model override for opt-in LLM stages.",
        )
        parser.add_argument(
            "--reasoning-mode",
            choices=("config", "keep", "strip"),
            default="config",
            help=(
                "Reasoning trace handling. 'config' strips reasoning only when a config file "
                "is provided and reasoning is disabled; 'keep' preserves reasoning; 'strip' "
                "always removes reasoning from outputs written by this run."
            ),
        )

        parser.add_argument(
            "--tasks",
            nargs="+",
            choices=tuple(DaftExportConfig.model_fields),
            default=None,
            help="Replace the configured task selection with exactly these tasks.",
        )
        for flag, value_type in (
            ("temperature", float),
            ("top-p", float),
            ("max-tokens", int),
            ("llm-retries", int),
        ):
            parser.add_argument(
                "--" + flag,
                type=value_type,
                default=None,
                help="Override this generation setting for enabled tasks only.",
            )
        for flag in (
            "open-qa-question-file",
            "bcq-question-file",
            "mcq-item-file",
            "temporal-localization-query-file",
            "causal-pair-file",
        ):
            parser.add_argument(
                "--" + flag,
                default=None,
                help="Task input file; does not enable the task.",
            )

    def execute(self, args: argparse.Namespace, data_entries: list[DataEntry]) -> None:
        with ExitStack() as stack:
            storage = MSCStorage(self.logger)
            snapshot = getattr(args, "config_snapshot", None)
            cfg_path: Path | None
            if args.config_file and storage.is_remote_storage_url(args.config_file):
                directory = stack.enter_context(
                    tempfile.TemporaryDirectory(prefix="reasoning_config_")
                )
                cfg_path = Path(directory) / "config.yaml"
                if snapshot is not None:
                    cfg_path.write_text(yaml.safe_dump(snapshot), encoding="utf-8")
                else:
                    cfg_path = Path(
                        storage.download_if_remote(args.config_file, str(cfg_path), is_file=True)
                    )
            else:
                cfg_path = (
                    Path(args.config_file).expanduser().resolve() if args.config_file else None
                )
            overrides = getattr(args, "config_overrides", [])
            cfg = (
                _load_config(cfg_path, snapshot=snapshot, args=args)
                if cfg_path is not None
                else _apply_cli_overrides({}, args)
                if overrides
                or any(
                    getattr(args, name, None) is not None
                    for name in ("tasks", *_GENERATION_FLAGS, *_INPUT_FLAGS)
                )
                else None
            )
            resolver = build_resolver(args, logger=self.logger)
            config_dir = cfg_path.parent if cfg_path is not None else Path.cwd()

            pipeline = LinearPipeline(
                tasks=[
                    DaftValidationTask(),
                    ReasoningTask(
                        config=cfg,
                        resolver=resolver,
                        config_dir=config_dir,
                        reasoning_mode=args.reasoning_mode,
                    ),
                    DaftValidationTask(),
                ],
                name="reasoning_pipeline",
                policy=EmptyOutputPolicy.FAIL,
            )
            processed = pipeline.run(data_entries)
            self.logger.info("Processed %d data entries.", len(processed))


def _load_config(
    path: Path,
    overrides: list[str] | None = None,
    *,
    snapshot: dict[str, Any] | None = None,
    args: argparse.Namespace | None = None,
) -> DaftExportConfig:
    """Load a task configuration and validate after applying CLI field overrides."""
    if snapshot is not None:
        loaded = dict(snapshot)
    else:
        loaded = read_config(str(path))
    if not isinstance(loaded, dict):
        raise ValueError(f"Reasoning config must be a JSON/YAML object: {path}")
    loaded.pop("cli", None)
    # A direct config may itself contain the reasoning-enrichment block.
    wrapped = loaded.get("reasoning")
    section = (
        wrapped
        if isinstance(wrapped, dict)
        and (
            "pipeline" in loaded
            or (
                not any(
                    key in DaftExportConfig.model_fields for key in loaded if key != "reasoning"
                )
                and any(key in DaftExportConfig.model_fields for key in wrapped)
            )
        )
        else loaded
    )
    if not isinstance(section, dict):
        raise ValueError(f"Reasoning config section must be an object: {path}")
    merged = override_config(section, overrides or [])
    return (
        _apply_cli_overrides(merged, args)
        if args is not None
        else DaftExportConfig.model_validate(merged)
    )


_GENERATION_FLAGS = {
    "temperature": "temperature",
    "top_p": "top_p",
    "max_tokens": "max_tokens",
    "llm_retries": "retries",
}
_INPUT_FLAGS = {
    "open_qa_question_file": ("open_qa", "question_file"),
    "bcq_question_file": ("bcq_openended", "question_file"),
    "mcq_item_file": ("mcq_openended", "item_file"),
    "temporal_localization_query_file": ("temporal_localization", "query_file"),
    "causal_pair_file": ("causal_linkage", "pair_file"),
}


def _apply_cli_overrides(
    config: dict[str, Any],
    args: argparse.Namespace,
) -> DaftExportConfig:
    """Merge file CLI defaults, advanced overrides, and explicit flags before validation."""
    values = override_config(config, [])

    overrides = getattr(args, "config_overrides", [])
    overridden = override_config({}, overrides)

    def apply(names: set[str], *, preserve_overrides: bool = False) -> None:
        tasks = getattr(args, "tasks", None)
        if "tasks" in names and tasks is not None:
            for name in DaftExportConfig.model_fields:
                if name in tasks or values.get(name) is not None:
                    values.setdefault(name, {})
                    if values[name] is None:
                        values[name] = {}
                    values[name]["enabled"] = name in tasks
        for argument, (task, field) in _INPUT_FLAGS.items():
            value = getattr(args, argument, None)
            if argument in names and value is not None:
                if values.get(task) is None:
                    values[task] = {}
                values[task][field] = value
        for name in DaftExportConfig.model_fields:
            section = values.get(name)
            if isinstance(section, dict) and section.get("enabled"):
                for argument, field in _GENERATION_FLAGS.items():
                    value = getattr(args, argument, None)
                    task_overrides = overridden.get(name)
                    if (
                        preserve_overrides
                        and isinstance(task_overrides, dict)
                        and field in task_overrides
                    ):
                        continue
                    if argument in names and value is not None:
                        section[field] = value

    names = {"tasks", *_GENERATION_FLAGS, *_INPUT_FLAGS}
    apply(names)
    values = override_config(values, overrides)
    explicit = getattr(args, "explicit_cli", names)
    # A task enabled by --set still inherits file CLI generation defaults.
    apply(set(_GENERATION_FLAGS) - explicit, preserve_overrides=True)
    apply(explicit)
    return DaftExportConfig.model_validate(values)


def build_resolver(args: argparse.Namespace, *, logger: logging.Logger) -> EndpointResolver:
    """Build the reasoning endpoint resolver from parsed CLI args."""
    resolver = EndpointResolver(None, logger=logger)
    resolver.apply_llm_overrides(
        url=getattr(args, "llm_endpoint_url", None) or "",
        model=getattr(args, "llm_model", None) or "",
    )
    return resolver


def main() -> None:
    ReasoningService().run()


if __name__ == "__main__":
    main()

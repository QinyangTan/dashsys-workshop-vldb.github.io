from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser() if value else default


def find_project_root(start: Path | None = None) -> Path:
    """Find the project root without relying on machine-local absolute paths."""
    explicit = os.getenv("DASHAGENT_ROOT")
    if explicit:
        return Path(explicit).expanduser().resolve()

    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "dashagent").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return current


@dataclass(frozen=True)
class Config:
    project_root: Path
    data_dir: Path
    dbsnapshot_dir: Path
    data_json_path: Path
    outputs_dir: Path
    prompts_dir: Path
    max_preview_chars: int = 1000
    max_result_rows: int = 50
    api_timeout_seconds: int = 15
    allow_unknown_api_endpoints: bool = False
    max_join_hints: int = 8
    max_gold_patterns: int = 2
    compact_metadata: bool = True
    relevance_top_k_tables: int = 8
    relevance_top_k_apis: int = 4
    fast_path_confidence_threshold: float = 0.0
    api_skip_confidence_threshold: float = 0.0
    disable_fast_paths: bool = False
    disable_gold_patterns: bool = False
    disable_context_cards: bool = False
    disable_api_fallback_templates: bool = False
    drop_one_join_hint: bool = False

    @classmethod
    def from_env(cls, root: Path | None = None) -> "Config":
        project_root = find_project_root(root)
        data_dir = _path_from_env("DASHAGENT_DATA_DIR", project_root / "data")
        outputs_dir = _path_from_env("DASHAGENT_OUTPUTS_DIR", project_root / "outputs")
        prompts_dir = _path_from_env("DASHAGENT_PROMPTS_DIR", project_root / "prompts")
        return cls(
            project_root=project_root,
            data_dir=data_dir,
            dbsnapshot_dir=_path_from_env("DASHAGENT_DBSNAPSHOT_DIR", data_dir / "DBSnapshot"),
            data_json_path=_path_from_env("DASHAGENT_DATA_JSON", data_dir / "data.json"),
            outputs_dir=outputs_dir,
            prompts_dir=prompts_dir,
            max_preview_chars=int(os.getenv("DASHAGENT_MAX_PREVIEW_CHARS", "1000")),
            max_result_rows=int(os.getenv("DASHAGENT_MAX_RESULT_ROWS", "50")),
            api_timeout_seconds=int(os.getenv("DASHAGENT_API_TIMEOUT_SECONDS", "15")),
            allow_unknown_api_endpoints=os.getenv("DASHAGENT_ALLOW_UNKNOWN_API", "0") == "1",
            max_join_hints=int(os.getenv("DASHAGENT_MAX_JOIN_HINTS", "8")),
            max_gold_patterns=int(os.getenv("DASHAGENT_MAX_GOLD_PATTERNS", "2")),
            compact_metadata=os.getenv("DASHAGENT_COMPACT_METADATA", "1") != "0",
            relevance_top_k_tables=int(os.getenv("DASHAGENT_RELEVANCE_TOP_K_TABLES", "8")),
            relevance_top_k_apis=int(os.getenv("DASHAGENT_RELEVANCE_TOP_K_APIS", "4")),
            fast_path_confidence_threshold=float(os.getenv("DASHAGENT_FAST_PATH_CONFIDENCE_THRESHOLD", "0.0")),
            api_skip_confidence_threshold=float(os.getenv("DASHAGENT_API_SKIP_CONFIDENCE_THRESHOLD", "0.0")),
            disable_fast_paths=os.getenv("DASHAGENT_DISABLE_FAST_PATHS", "0") == "1",
            disable_gold_patterns=os.getenv("DASHAGENT_DISABLE_GOLD_PATTERNS", "0") == "1",
            disable_context_cards=os.getenv("DASHAGENT_DISABLE_CONTEXT_CARDS", "0") == "1",
            disable_api_fallback_templates=os.getenv("DASHAGENT_DISABLE_API_FALLBACK_TEMPLATES", "0") == "1",
            drop_one_join_hint=os.getenv("DASHAGENT_DROP_ONE_JOIN_HINT", "0") == "1",
        )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dbsnapshot_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG = Config.from_env()

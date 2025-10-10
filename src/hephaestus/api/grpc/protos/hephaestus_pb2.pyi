from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GuardRailsRequest(_message.Message):
    __slots__ = ("no_format", "workspace", "drift_check", "env", "auto_remediate")

    class EnvEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

    NO_FORMAT_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    DRIFT_CHECK_FIELD_NUMBER: _ClassVar[int]
    ENV_FIELD_NUMBER: _ClassVar[int]
    AUTO_REMEDIATE_FIELD_NUMBER: _ClassVar[int]
    no_format: bool
    workspace: str
    drift_check: bool
    env: _containers.ScalarMap[str, str]
    auto_remediate: bool
    def __init__(
        self,
        no_format: bool = ...,
        workspace: _Optional[str] = ...,
        drift_check: bool = ...,
        env: _Optional[_Mapping[str, str]] = ...,
        auto_remediate: bool = ...,
    ) -> None: ...

class GuardRailsResponse(_message.Message):
    __slots__ = ("success", "gates", "duration", "task_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    GATES_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    gates: _containers.RepeatedCompositeFieldContainer[QualityGateResult]
    duration: float
    task_id: str
    def __init__(
        self,
        success: bool = ...,
        gates: _Optional[_Iterable[_Union[QualityGateResult, _Mapping]]] = ...,
        duration: _Optional[float] = ...,
        task_id: _Optional[str] = ...,
    ) -> None: ...

class GuardRailsProgress(_message.Message):
    __slots__ = ("stage", "progress", "message", "completed")
    STAGE_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    stage: str
    progress: int
    message: str
    completed: bool
    def __init__(
        self,
        stage: _Optional[str] = ...,
        progress: _Optional[int] = ...,
        message: _Optional[str] = ...,
        completed: bool = ...,
    ) -> None: ...

class QualityGateResult(_message.Message):
    __slots__ = ("name", "passed", "message", "duration", "metadata")

    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

    NAME_FIELD_NUMBER: _ClassVar[int]
    PASSED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    name: str
    passed: bool
    message: str
    duration: float
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        name: _Optional[str] = ...,
        passed: bool = ...,
        message: _Optional[str] = ...,
        duration: _Optional[float] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class DriftRequest(_message.Message):
    __slots__ = ("workspace",)
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    workspace: str
    def __init__(self, workspace: _Optional[str] = ...) -> None: ...

class DriftResponse(_message.Message):
    __slots__ = ("has_drift", "drifts", "remediation_commands")
    HAS_DRIFT_FIELD_NUMBER: _ClassVar[int]
    DRIFTS_FIELD_NUMBER: _ClassVar[int]
    REMEDIATION_COMMANDS_FIELD_NUMBER: _ClassVar[int]
    has_drift: bool
    drifts: _containers.RepeatedCompositeFieldContainer[ToolDrift]
    remediation_commands: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        has_drift: bool = ...,
        drifts: _Optional[_Iterable[_Union[ToolDrift, _Mapping]]] = ...,
        remediation_commands: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class ToolDrift(_message.Message):
    __slots__ = ("tool", "expected_version", "installed_version", "status")
    TOOL_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_VERSION_FIELD_NUMBER: _ClassVar[int]
    INSTALLED_VERSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    tool: str
    expected_version: str
    installed_version: str
    status: str
    def __init__(
        self,
        tool: _Optional[str] = ...,
        expected_version: _Optional[str] = ...,
        installed_version: _Optional[str] = ...,
        status: _Optional[str] = ...,
    ) -> None: ...

class CleanupRequest(_message.Message):
    __slots__ = ("root", "deep_clean", "dry_run", "patterns")
    ROOT_FIELD_NUMBER: _ClassVar[int]
    DEEP_CLEAN_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    PATTERNS_FIELD_NUMBER: _ClassVar[int]
    root: str
    deep_clean: bool
    dry_run: bool
    patterns: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        root: _Optional[str] = ...,
        deep_clean: bool = ...,
        dry_run: bool = ...,
        patterns: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class CleanupResponse(_message.Message):
    __slots__ = ("files_deleted", "size_freed", "deleted_paths", "manifest")

    class ManifestEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    FILES_DELETED_FIELD_NUMBER: _ClassVar[int]
    SIZE_FREED_FIELD_NUMBER: _ClassVar[int]
    DELETED_PATHS_FIELD_NUMBER: _ClassVar[int]
    MANIFEST_FIELD_NUMBER: _ClassVar[int]
    files_deleted: int
    size_freed: int
    deleted_paths: _containers.RepeatedScalarFieldContainer[str]
    manifest: _containers.ScalarMap[str, int]
    def __init__(
        self,
        files_deleted: _Optional[int] = ...,
        size_freed: _Optional[int] = ...,
        deleted_paths: _Optional[_Iterable[str]] = ...,
        manifest: _Optional[_Mapping[str, int]] = ...,
    ) -> None: ...

class CleanupPreview(_message.Message):
    __slots__ = ("files_to_delete", "size_to_free", "paths", "preview_manifest")

    class PreviewManifestEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

    FILES_TO_DELETE_FIELD_NUMBER: _ClassVar[int]
    SIZE_TO_FREE_FIELD_NUMBER: _ClassVar[int]
    PATHS_FIELD_NUMBER: _ClassVar[int]
    PREVIEW_MANIFEST_FIELD_NUMBER: _ClassVar[int]
    files_to_delete: int
    size_to_free: int
    paths: _containers.RepeatedScalarFieldContainer[str]
    preview_manifest: _containers.ScalarMap[str, int]
    def __init__(
        self,
        files_to_delete: _Optional[int] = ...,
        size_to_free: _Optional[int] = ...,
        paths: _Optional[_Iterable[str]] = ...,
        preview_manifest: _Optional[_Mapping[str, int]] = ...,
    ) -> None: ...

class RankingsRequest(_message.Message):
    __slots__ = ("strategy", "limit", "workspace")
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    strategy: str
    limit: int
    workspace: str
    def __init__(
        self,
        strategy: _Optional[str] = ...,
        limit: _Optional[int] = ...,
        workspace: _Optional[str] = ...,
    ) -> None: ...

class RankingsResponse(_message.Message):
    __slots__ = ("rankings", "strategy")
    RANKINGS_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    rankings: _containers.RepeatedCompositeFieldContainer[FileRanking]
    strategy: str
    def __init__(
        self,
        rankings: _Optional[_Iterable[_Union[FileRanking, _Mapping]]] = ...,
        strategy: _Optional[str] = ...,
    ) -> None: ...

class FileRanking(_message.Message):
    __slots__ = ("file", "score", "metrics")

    class MetricsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...

    FILE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    file: str
    score: float
    metrics: _containers.ScalarMap[str, float]
    def __init__(
        self,
        file: _Optional[str] = ...,
        score: _Optional[float] = ...,
        metrics: _Optional[_Mapping[str, float]] = ...,
    ) -> None: ...

class HotspotsRequest(_message.Message):
    __slots__ = ("workspace", "limit")
    WORKSPACE_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    workspace: str
    limit: int
    def __init__(self, workspace: _Optional[str] = ..., limit: _Optional[int] = ...) -> None: ...

class HotspotsResponse(_message.Message):
    __slots__ = ("hotspots",)
    HOTSPOTS_FIELD_NUMBER: _ClassVar[int]
    hotspots: _containers.RepeatedCompositeFieldContainer[Hotspot]
    def __init__(self, hotspots: _Optional[_Iterable[_Union[Hotspot, _Mapping]]] = ...) -> None: ...

class Hotspot(_message.Message):
    __slots__ = ("file", "change_frequency", "complexity", "risk_score")
    FILE_FIELD_NUMBER: _ClassVar[int]
    CHANGE_FREQUENCY_FIELD_NUMBER: _ClassVar[int]
    COMPLEXITY_FIELD_NUMBER: _ClassVar[int]
    RISK_SCORE_FIELD_NUMBER: _ClassVar[int]
    file: str
    change_frequency: int
    complexity: int
    risk_score: float
    def __init__(
        self,
        file: _Optional[str] = ...,
        change_frequency: _Optional[int] = ...,
        complexity: _Optional[int] = ...,
        risk_score: _Optional[float] = ...,
    ) -> None: ...

class AnalyticsEvent(_message.Message):
    __slots__ = ("source", "kind", "value", "unit", "metrics", "metadata", "timestamp")

    class MetricsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...

    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

    SOURCE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    source: str
    kind: str
    value: float
    unit: str
    metrics: _containers.ScalarMap[str, float]
    metadata: _containers.ScalarMap[str, str]
    timestamp: str
    def __init__(
        self,
        source: _Optional[str] = ...,
        kind: _Optional[str] = ...,
        value: _Optional[float] = ...,
        unit: _Optional[str] = ...,
        metrics: _Optional[_Mapping[str, float]] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
        timestamp: _Optional[str] = ...,
    ) -> None: ...

class AnalyticsIngestResponse(_message.Message):
    __slots__ = ("accepted", "rejected")
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    REJECTED_FIELD_NUMBER: _ClassVar[int]
    accepted: int
    rejected: int
    def __init__(self, accepted: _Optional[int] = ..., rejected: _Optional[int] = ...) -> None: ...

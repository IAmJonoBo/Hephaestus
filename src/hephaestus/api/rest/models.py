"""Pydantic models for REST API request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GuardRailsRequest(BaseModel):
    """Request schema for guard-rails endpoint."""

    no_format: bool = Field(
        default=False,
        description="Skip formatting step",
    )
    workspace: str | None = Field(
        default=None,
        description="Workspace directory path",
    )
    drift_check: bool = Field(
        default=False,
        description="Check for tool version drift",
    )


class QualityGateResult(BaseModel):
    """Result of a single quality gate."""

    name: str = Field(description="Gate name")
    passed: bool = Field(description="Whether gate passed")
    message: str | None = Field(default=None, description="Result message")
    duration: float | None = Field(default=None, description="Execution duration in seconds")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GuardRailsResponse(BaseModel):
    """Response schema for guard-rails endpoint."""

    success: bool = Field(description="Whether all gates passed")
    gates: list[dict[str, Any]] = Field(description="Results for each gate")
    duration: float = Field(description="Total duration in seconds")
    task_id: str = Field(description="Task identifier for tracking")


class CleanupRequest(BaseModel):
    """Request schema for cleanup endpoint."""

    root: str | None = Field(
        default=None,
        description="Root directory to clean",
    )
    deep_clean: bool = Field(
        default=False,
        description="Perform deep cleanup including git and virtualenvs",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview changes without executing",
    )


class CleanupResponse(BaseModel):
    """Response schema for cleanup endpoint."""

    files_deleted: int = Field(description="Number of files deleted")
    size_freed: int = Field(description="Bytes freed")
    manifest: dict[str, Any] = Field(description="Cleanup manifest")


class RankingsRequest(BaseModel):
    """Request schema for rankings endpoint."""

    strategy: str = Field(
        default="risk_weighted",
        description="Ranking strategy (risk_weighted, coverage_first, churn_based, composite)",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results",
    )


class RankingsResponse(BaseModel):
    """Response schema for rankings endpoint."""

    rankings: list[dict[str, Any]] = Field(description="Module rankings")
    strategy: str = Field(description="Strategy used")


class TaskStatusResponse(BaseModel):
    """Response schema for task status endpoint."""

    task_id: str = Field(description="Task identifier")
    status: str = Field(description="Task status (pending, running, completed, failed)")
    progress: float = Field(description="Progress percentage (0.0 to 1.0)")
    result: dict[str, Any] | None = Field(default=None, description="Task result if completed")
    error: str | None = Field(default=None, description="Error message if failed")

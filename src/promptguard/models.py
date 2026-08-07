from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Expect(BaseModel):
    """Deterministic expectations for a single case."""

    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)
    regex: list[str] = Field(default_factory=list)
    exact: Optional[str] = None
    json_valid: bool = False
    json_keys: list[str] = Field(default_factory=list)
    similar_to: Optional[str] = None
    min_similarity: float = 0.5
    max_chars: Optional[int] = None


class Message(BaseModel):
    role: str  # system | user | assistant
    content: str


class Case(BaseModel):
    id: str
    input: Optional[str] = None
    messages: list[Message] = Field(default_factory=list)
    expect: Expect = Field(default_factory=Expect)
    system_extra: Optional[str] = None
    vars: dict[str, Any] = Field(default_factory=dict)


class Suite(BaseModel):
    name: str
    system_prompt: str = ""
    # Optional path relative to suite file or absolute — loaded at runtime
    system_prompt_file: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    vars: dict[str, Any] = Field(default_factory=dict)
    cases: list[Case] = Field(default_factory=list)


class Failure(BaseModel):
    check: str
    message: str
    expected: Optional[str] = None
    got: Optional[str] = None


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    output: str
    failures: list[Failure] = Field(default_factory=list)
    latency_ms: Optional[float] = None
    rendered_input: Optional[str] = None


class RunResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    suite_name: str
    model: str
    temperature: float
    system_prompt: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    passed: int = 0
    failed: int = 0
    total: int = 0
    case_results: list[CaseResult] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

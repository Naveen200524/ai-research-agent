from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SearchEngineType(str, Enum):
    DUCKDUCKGO = "duckduckgo"
    BRAVE = "brave"

class SummaryStyle(str, Enum):
    COMPREHENSIVE = "comprehensive"
    BRIEF = "brief"
    TECHNICAL = "technical"

class TimeFreshness(str, Enum):
    ALL_TIME = None
    PAST_DAY = "pd"
    PAST_WEEK = "pw"
    PAST_MONTH = "pm"
    PAST_YEAR = "py"

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    max_results: int = Field(default=10, ge=5, le=20)
    freshness: Optional[str] = None
    style: SummaryStyle = SummaryStyle.COMPREHENSIVE
    search_engines: List[SearchEngineType] = [SearchEngineType.DUCKDUCKGO]

class ResearchResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    started_at: datetime
    error: Optional[str] = None

class SearchResult(BaseModel):
    title: str
    url: str
    description: str
    source: str
    relevance_score: float = Field(ge=0, le=1)
    age: Optional[str] = None

class ExtractedContent(BaseModel):
    url: str
    title: str
    text: str
    success: bool
    error: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    source_engine: Optional[str] = None

class Source(BaseModel):
    id: int
    title: str
    url: str
    domain: str
    cited: bool
    source_engine: str

class ResearchSummary(BaseModel):
    summary: str
    sections: Dict[str, str]
    sources: List[Source]
    generated_at: datetime
    word_count: int
    model_used: str
    provider: str
    cost: float

class ResearchResult(BaseModel):
    job_id: str
    query: str
    search_engines_used: List[str]
    search_results: List[SearchResult]
    extracted_count: int
    summary: ResearchSummary
    completed_at: datetime
    from_cache: bool = False
    cache_type: Optional[str] = None
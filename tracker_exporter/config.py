import datetime
import logging

from functools import lru_cache
from typing import Literal, Optional, Union
from pydantic import validator, root_validator
from pydantic_settings import BaseSettings

from tracker_exporter.models.base import YandexTrackerLanguages, LogLevels
from tracker_exporter.exceptions import ConfigurationError
from tracker_exporter.services.monitoring import DogStatsdClient

YANDEX_TRACKER_API_SEARCH_HARD_LIMIT = 10000
YANDEX_TRACKER_HARD_LIMIT_ISSUE_URL = "https://github.com/yandex/yandex_tracker_client/issues/13"

logger = logging.getLogger(__name__)


class MonitoringSettings(BaseSettings):
    """Observability settings."""

    metrics_enabled: Optional[bool] = False
    metrics_host: Optional[str] = "localhost"
    metrics_port: Optional[int] = 8125
    metrics_base_prefix: Optional[str] = "tracker_exporter"
    metrics_base_labels: Optional[list[str]] = []
    sentry_enabled: Optional[bool] = False
    sentry_dsn: Optional[str] = None


    class Config:
        extra = "ignore"


class ClickhouseSettings(BaseSettings):
    """Settings for Clickhouse storage."""

    enable_upload: Optional[bool] = True
    host: Optional[str] = "localhost"
    proto: Optional[str] = "http"
    port: Optional[int] = 8123
    cacert_path: Optional[str] = None
    serverless_proxy_id: str | None = None
    username: Optional[str] = "default"
    password: Optional[str] = None
    database: Optional[str] = "agile"
    issues_table: Optional[str] = "issues"
    issue_metrics_table: Optional[str] = "issue_metrics"
    issues_changelog_table: Optional[str] = "issues_changelog"
    auto_deduplicate: Optional[bool] = True
    backoff_base_delay: Optional[Union[int, float]] = 0.5
    backoff_expo_factor: Optional[Union[int, float]] = 2.5
    backoff_max_tries: Optional[int] = 3
    backoff_jitter: Optional[bool] = True



    class Config:
        extra = "ignore"


class IssuesSearchSettings(BaseSettings):
    """Settings for search & export."""

    query: Optional[str] = None
    range: Optional[str] = "2h"
    queues: Optional[Union[str, list[str]]] = None
    per_page_limit: Optional[int] = 100


    class Config:
        extra = "ignore"


class TrackerSettings(BaseSettings):
    """Settings for Yandex.Tracker client."""

    loglevel: Optional[LogLevels] = LogLevels.warning
    token: Optional[str] = None
    org_id: Optional[str] = None
    iam_token: Optional[str] = None
    cloud_org_id: Optional[str] = None
    timeout: Optional[int] = 10
    max_retries: Optional[int] = 10
    language: Optional[YandexTrackerLanguages] = YandexTrackerLanguages.en
    timezone: Optional[str] = "Europe/Moscow"
    search: IssuesSearchSettings = IssuesSearchSettings()


    class Config:
        extra = "ignore"


class StateSettings(BaseSettings):
    """Settings for stateful mode."""

    storage: Optional[Literal["redis", "jsonfile", "custom"]] = "jsonfile"
    redis_dsn: Optional[str] = "redis://localhost:6379"
    jsonfile_strategy: Optional[Literal["s3", "local"]] = "local"
    jsonfile_path: Optional[str] = "state.json"
    jsonfile_s3_bucket: Optional[str] = None
    jsonfile_s3_region: Optional[str] = "us-east-1"
    jsonfile_s3_endpoint: Optional[str] = None
    jsonfile_s3_access_key: Optional[str] = None
    jsonfile_s3_secret_key: Optional[str] = None
    custom_storage_params: Optional[dict] = {}


    class Config:
        extra = "ignore"


class Settings(BaseSettings):
    """Global merged config."""

    monitoring: MonitoringSettings = MonitoringSettings()
    clickhouse: ClickhouseSettings = ClickhouseSettings()
    tracker: TrackerSettings = TrackerSettings  # TODO (akimrx): research, called class not see TOKEN's
    state: StateSettings = StateSettings()
    stateful: Optional[bool] = False
    stateful_initial_range: Optional[str] = "1w"
    changelog_export_enabled: Optional[bool] = False
    log_etl_stats: Optional[bool] = True
    log_etl_stats_each_n_iter: Optional[int] = 100

    loglevel: Optional[LogLevels] = LogLevels.info
    workdays: Optional[list[int]] = [0, 1, 2, 3, 4]
    business_hours_start: Optional[datetime.time] = datetime.time(9)
    business_hours_end: Optional[datetime.time] = datetime.time(22)
    datetime_response_format: Optional[str] = "%Y-%m-%dT%H:%M:%S.%f%z"
    datetime_query_format: Optional[str] = "%Y-%m-%d %H:%M:%S"
    datetime_clickhouse_format: Optional[str] = "%Y-%m-%dT%H:%M:%S.%f"

    etl_interval_minutes: Optional[int] = 30
    closed_issue_statuses: Optional[Union[str, list]] = "closed,rejected,resolved,cancelled,released"
    not_nullable_fields: Optional[Union[tuple, list, str]] = (
        "created_at",
        "resolved_at",
        "closed_at",
        "updated_at",
        "released_at",
        "deadline",
        "start_date",
        "end_date",
        "start_time",
        "end_time",
        "moved_at",
    )



    class Config:
        env_prefix = "EXPORTER_"
        case_sensitive = False
        env_nested_delimiter = "__"
        env_file = ".env"
        extra = "ignore"


@lru_cache
def _get_settings():
    cfg = Settings()
    return cfg


config = _get_settings()
monitoring = DogStatsdClient(
    host=config.monitoring.metrics_host,
    port=config.monitoring.metrics_port,
    base_labels=config.monitoring.metrics_base_labels,
    metric_name_prefix=config.monitoring.metrics_base_prefix,
    use_ms=True,
    enabled=config.monitoring.metrics_enabled,
)

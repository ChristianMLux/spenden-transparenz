"""Configuration rules that are security rules.

The two that matter most: production refuses to start without its secrets, and this module never
reads AthenaRun's .env.platform. The second one is a scope rule - this is not an AthenaRun product
and must not inherit AthenaRun credentials by accident.
"""

import ast
import inspect

import core.settings
import pytest
from core.settings import Settings
from pydantic import ValidationError

DOCSTRING_NODES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

VALID_DB = "postgresql+asyncpg://user:pass@localhost:5432/spenden"
VALID_TOKEN = "t" * 32


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("ENV", "ADMIN_TOKEN", "DATABASE_URL", "DATABASE_URL_SYNC", "ANTHROPIC_API_KEY", "LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)


def test_production_refuses_to_start_without_admin_token():
    with pytest.raises(ValidationError, match="ADMIN_TOKEN"):
        Settings(env="production", database_url=VALID_DB, _env_file=None)


def test_production_refuses_to_start_without_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(env="production", admin_token=VALID_TOKEN, _env_file=None)


def test_production_refuses_an_admin_token_shorter_than_32_bytes():
    with pytest.raises(ValidationError, match="32"):
        Settings(env="production", admin_token="tooshort", database_url=VALID_DB, _env_file=None)


def test_production_accepts_a_full_configuration():
    s = Settings(env="production", admin_token=VALID_TOKEN, database_url=VALID_DB, _env_file=None)
    assert s.env == "production"


def test_development_starts_without_any_secret():
    s = Settings(_env_file=None)
    assert s.env == "development" and s.admin_token is None


def test_sync_url_is_derived_from_the_async_url():
    s = Settings(database_url=VALID_DB, _env_file=None)
    assert s.sync_url == "postgresql+psycopg://user:pass@localhost:5432/spenden"


def test_an_explicit_sync_url_wins():
    s = Settings(database_url=VALID_DB, database_url_sync="postgresql+psycopg://other/db", _env_file=None)
    assert s.sync_url == "postgresql+psycopg://other/db"


def test_a_bare_postgres_url_gets_the_asyncpg_driver():
    s = Settings(database_url="postgresql://user:pass@host/db", _env_file=None)
    assert s.async_url == "postgresql+asyncpg://user:pass@host/db"
    assert s.sync_url == "postgresql+psycopg://user:pass@host/db"


def test_async_url_without_a_database_url_fails_loudly():
    s = Settings(_env_file=None)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _ = s.async_url


def test_settings_never_read_the_athenarun_platform_env_file():
    """No string this module can turn into a path may point outside this repository.

    Checked against string literals rather than the whole source, so the module can explain the
    rule in a comment without tripping over it. A future `.env.platform` fallback fails here.
    """
    tree = ast.parse(inspect.getsource(core.settings))
    docstring_ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, DOCSTRING_NODES) and body and isinstance(body[0], ast.Expr):
            first = body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                docstring_ids.add(id(first))
    literals = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstring_ids
    ]
    for literal in literals:
        assert "platform" not in literal.lower(), literal
        assert "athenarun" not in literal.lower(), literal
        assert ".." not in literal, literal


def test_secrets_do_not_leak_into_repr_or_model_dump():
    s = Settings(admin_token="a" * 40, anthropic_api_key="sk-ant-secret-value", _env_file=None)
    text = repr(s) + str(s.model_dump()) + str(s)
    assert "sk-ant-secret-value" not in text
    assert "a" * 40 not in text


def test_the_admin_token_is_still_readable_where_it_is_needed():
    s = Settings(admin_token=VALID_TOKEN, _env_file=None)
    assert s.admin_token.get_secret_value() == VALID_TOKEN


def test_get_settings_is_cached():
    core.settings.get_settings.cache_clear()
    assert core.settings.get_settings() is core.settings.get_settings()


def test_ingestion_limits_have_the_spec_defaults():
    s = Settings(_env_file=None)
    assert s.max_reports_per_run == 25
    assert s.max_run_cost_usd == 1.0
    assert s.reliefweb_min_interval_s == 2.0
    assert "reliefweb.int" in s.allowed_fetch_hosts


def test_the_user_agent_is_honest_and_carries_a_contact():
    s = Settings(_env_file=None)
    assert "spenden-transparenz" in s.user_agent
    assert "@" in s.user_agent or "http" in s.user_agent


def test_cors_origins_are_never_a_wildcard():
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_origins=["*"], _env_file=None)

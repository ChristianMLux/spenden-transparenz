"""Revalidation is a cache hint. It must never turn a successful ingestion into a failed one."""

from __future__ import annotations

import pytest
import requests
from core.settings import Settings

from pipeline.revalidate import crisis_tag, org_tag, revalidate


def _settings(**kw) -> Settings:
    base = {"web_base_url": "https://web.example", "revalidate_secret": "s" * 16, "_env_file": None}
    return Settings(**{**base, **kw})


def test_tags_are_built_in_the_shape_the_web_app_expects():
    assert crisis_tag("ff-2026-000162-npl") == "crisis:ff-2026-000162-npl"
    assert org_tag("nepal-red-cross-society") == "org:nepal-red-cross-society"


def test_nothing_happens_when_it_is_not_configured():
    assert revalidate(["crisis:x"], _settings(web_base_url=None)) == 0
    assert revalidate(["crisis:x"], _settings(revalidate_secret=None)) == 0


def test_a_successful_call_is_counted(httpserver):
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_json({"revalidated": "crisis:x"})
    accepted = revalidate(["crisis:x"], _settings(web_base_url=httpserver.url_for("")))
    assert accepted == 1


def test_the_bearer_token_is_sent(httpserver):
    httpserver.expect_request(
        "/api/revalidate", method="POST", headers={"Authorization": "Bearer " + "s" * 16}
    ).respond_with_json({"revalidated": "crisis:x"})
    assert revalidate(["crisis:x"], _settings(web_base_url=httpserver.url_for(""))) == 1


def test_duplicate_tags_are_sent_once(httpserver):
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_json({"revalidated": "ok"})
    accepted = revalidate(["crisis:x", "crisis:x", "org:a", "org:a"], _settings(web_base_url=httpserver.url_for("")))
    assert accepted == 2


def test_a_malformed_tag_never_leaves_the_machine(httpserver):
    """Matching the web app's own pattern locally means a bad tag is named in our log rather than
    coming back as an opaque 400."""
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_json({"revalidated": "ok"})
    assert revalidate(["Crisis:UPPER", "nope", "org:has spaces"], _settings(web_base_url=httpserver.url_for(""))) == 0


def test_a_401_is_logged_and_not_raised(httpserver):
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_data("", status=401)
    assert revalidate(["crisis:x"], _settings(web_base_url=httpserver.url_for(""))) == 0


def test_a_500_is_logged_and_not_raised(httpserver):
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_data("", status=500)
    assert revalidate(["crisis:x"], _settings(web_base_url=httpserver.url_for(""))) == 0


def test_an_unreachable_web_app_does_not_raise():
    """The rows are already committed when this runs. A web app that is down must not make the
    ingestion look failed."""
    assert revalidate(["crisis:x"], _settings(web_base_url="http://127.0.0.1:1")) == 0


def test_a_timeout_does_not_raise(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.Timeout("too slow")

    monkeypatch.setattr(requests.Session, "post", boom)
    assert revalidate(["crisis:x"], _settings()) == 0


@pytest.mark.parametrize("tag", ["crisis:ff-2026-000162-npl", "org:nepal-red-cross-society", "org:a-b-c-1"])
def test_valid_tags_match_the_contract_pattern(tag, httpserver):
    httpserver.expect_request("/api/revalidate", method="POST").respond_with_json({"revalidated": tag})
    assert revalidate([tag], _settings(web_base_url=httpserver.url_for(""))) == 1

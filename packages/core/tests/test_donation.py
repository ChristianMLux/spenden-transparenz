"""The official-domain rule.

The one place on this board where a reader acts with money, so the one place where a wrong URL
costs them something real.
"""

from __future__ import annotations

import pytest
from core.donation import host_of, is_official_domain, registrable_domain


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.care.org/donate/", "care.org"),
        ("https://donation.nrcs.org/", "nrcs.org"),
        ("nepal.oxfam.org", "oxfam.org"),
        ("https://www.opmcm.gov.np", "opmcm.gov.np"),
        ("https://ndrrma.gov.np/anything?x=1", "ndrrma.gov.np"),
        ("https://a.b.c.example.co.uk/", "example.co.uk"),
        ("org.np", None),
        ("gov.np", None),
        ("localhost", None),
        ("", None),
        (None, None),
    ],
)
def test_registrable_domain(url, expected):
    assert registrable_domain(url) == expected


def test_host_of_reads_a_bare_domain_as_a_host_not_a_path():
    """Websites are written without a scheme in the source records."""
    assert host_of("carenepal.org") == "carenepal.org"
    assert host_of("https://www.carenepal.org/x") == "carenepal.org"


def test_a_subdomain_of_the_website_is_official():
    assert is_official_domain("https://donation.nrcs.org/", "https://nrcs.org")


def test_the_parent_domain_is_official_when_the_website_is_a_subdomain():
    """Oxfam in Nepal's site is nepal.oxfam.org and it donates through oxfam.org. Same registrant,
    so the same registrable domain - the rule is about who owns the name, not about depth."""
    assert is_official_domain("https://www.oxfam.org/en/donate", "https://nepal.oxfam.org")


def test_a_different_legal_entity_is_not_official():
    """The rejection this rule caught on its first pass over the researched file: CARE Nepal
    (carenepal.org) with a donation link on care.org, which is CARE USA. A donor following it
    would be giving to an organisation this board never told them about."""
    assert not is_official_domain("https://www.care.org/donate/", "https://carenepal.org")


@pytest.mark.parametrize(
    "third_party",
    [
        "https://www.gofundme.com/f/nepal-floods",
        "https://donate.example-aggregator.com/nrcs",
        "https://nrcs.org.evil.example/donate",
    ],
)
def test_a_third_party_url_is_never_official(third_party):
    assert not is_official_domain(third_party, "https://nrcs.org")


def test_two_organisations_under_one_public_suffix_do_not_match():
    """The failure mode a missing multi-label suffix would create: every .org.np organisation
    sharing one registrable domain, so any of their links would validate against any other."""
    assert not is_official_domain("https://someone-else.org.np/donate", "https://nrcs.org.np")


def test_an_organisation_without_a_website_has_nothing_to_verify_against():
    """A gap in the record is not a licence to trust an unverifiable link."""
    assert not is_official_domain("https://donation.nrcs.org/", None)
    assert not is_official_domain("https://donation.nrcs.org/", "")

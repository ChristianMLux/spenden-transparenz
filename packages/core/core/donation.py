"""The official-domain rule for a donation channel.

A donation link is the one place on this board where a reader acts with money, so it is the one
place where a wrong URL costs them something real. The rule is therefore narrow: a donation URL is
only stored when it lives on the organisation's own registrable domain. A third-party page - a
fundraising platform, an aggregator, a lookalike - never enters the database, however plausible it
looks, and no account numbers are stored anywhere.

The rule is not merely defensive. Running it over the researched file rejected exactly one entry:
CARE Nepal (carenepal.org) with a donation link on care.org, which is CARE USA - a different legal
entity in a different country. A donor following that link would be giving to an organisation this
board never told them about. That is the failure the rule exists to catch, and it caught it on the
first pass over real data.
"""

from __future__ import annotations

from urllib.parse import urlsplit

# Second-level public suffixes, i.e. the ones under which anybody may register a name, so the
# registrable domain is the THIRD label from the right rather than the second. Covering the wrong
# way round is what matters here: a suffix missing from this table makes the rule too LOOSE (two
# unrelated organisations under the same suffix would appear to share a domain), while a suffix
# listed in error only makes it stricter and costs a rejection someone will see in the log.
#
# Deliberately a table and not the full Public Suffix List: this project has no PSL dependency,
# and the dataset is Nepal plus internationally registered NGOs. Nepal's own suffixes are the ones
# that must be right, and they are. Extend it when a new jurisdiction appears in the data.
MULTI_LABEL_SUFFIXES = frozenset(
    {
        # Nepal - the jurisdiction this product is about
        "gov.np",
        "org.np",
        "com.np",
        "edu.np",
        "net.np",
        "mil.np",
        "info.np",
        # Jurisdictions the pilot organisations are registered in
        "co.uk",
        "org.uk",
        "ac.uk",
        "gov.uk",
        "me.uk",
        "net.uk",
        "plc.uk",
        "ltd.uk",
        "com.au",
        "org.au",
        "net.au",
        "gov.au",
        "edu.au",
        "asn.au",
        "co.in",
        "org.in",
        "net.in",
        "gov.in",
        "ac.in",
        "co.nz",
        "org.nz",
        "govt.nz",
        "ac.nz",
        "co.za",
        "org.za",
        "gov.za",
        "co.jp",
        "or.jp",
        "go.jp",
        "ac.jp",
        "com.br",
        "org.br",
        "gov.br",
        "co.kr",
        "or.kr",
        "go.kr",
        "com.cn",
        "org.cn",
        "gov.cn",
        "edu.cn",
        "com.hk",
        "org.hk",
        "gov.hk",
        "com.sg",
        "org.sg",
        "gov.sg",
        "com.my",
        "org.my",
        "gov.my",
        "com.pk",
        "org.pk",
        "gov.pk",
        "com.bd",
        "org.bd",
        "gov.bd",
        "lk.org",
        "com.lk",
        "org.lk",
        "gov.lk",
    }
)


def host_of(url: str | None) -> str | None:
    """Lowercased hostname without a leading "www.", or None when there is no host to read.

    A bare "example.org" with no scheme is read as a host rather than as a path, because that is
    how websites are written in the source records.
    """
    if not url or not url.strip():
        return None
    candidate = url.strip()
    if "//" not in candidate:
        candidate = "https://" + candidate
    hostname = urlsplit(candidate).hostname
    if not hostname:
        return None
    return hostname.lower().removeprefix("www.")


def registrable_domain(url: str | None) -> str | None:
    """The registered name plus its public suffix - "nrcs.org" for "donation.nrcs.org".

    None when there is no host, or when the host is nothing but a public suffix and therefore
    names no registrant at all ("org.np" on its own).
    """
    host = host_of(url)
    if not host or "." not in host:
        return None
    labels = host.split(".")
    if ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
        return ".".join(labels[-3:]) if len(labels) >= 3 else None
    return ".".join(labels[-2:])


def is_official_domain(donation_url: str | None, website: str | None) -> bool:
    """True when the donation URL sits on the organisation's own registrable domain.

    A subdomain passes ("donation.nrcs.org" for "nrcs.org") and so does the parent when the
    website itself is a subdomain ("oxfam.org" for "nepal.oxfam.org"): both are the same
    registrant. A different registrable domain never passes, which is what separates CARE Nepal
    from CARE USA.

    An organisation with no website of its own has nothing to check against, so nothing passes.
    That is a gap in the record, not a licence to trust an unverifiable link.
    """
    donation = registrable_domain(donation_url)
    return donation is not None and donation == registrable_domain(website)

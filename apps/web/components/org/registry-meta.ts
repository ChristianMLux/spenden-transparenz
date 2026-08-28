/**
 * A registration row whose identifier is a gap often still has a fixed, well-known
 * register behind it (the pilot data's NP_SWC row has `url: null` precisely because the
 * fetch that would have produced a URL failed). The domain named in the honest sentence
 * ("Quelle nicht erreichbar (swc.org.np, 28.08.2026)", DESIGN.md 8.3) describes the
 * registry itself, not this org's particular row, so it is looked up here rather than
 * read off `registration.register_url`, which is null exactly when it would be needed.
 *
 * `null` means the registry has no single domain worth naming in a sentence (OTHER is a
 * catch-all; UN is not one website).
 */
const REGISTRY_DOMAIN: Record<string, string | null> = {
  NP_SWC: "swc.org.np",
  NP_DAO: null,
  IATI: "iatistandard.org",
  US_IRS: "irs.gov",
  DE_DZI: "dzi.de",
  DE_ITZ: "transparente-zivilgesellschaft.de",
  DE_VEREINSREGISTER: null,
  UK_CC: "register-of-charities.charitycommission.gov.uk",
  CH_ZEWO: "zewo.ch",
  UN: null,
  OTHER: null,
};

export function registryDomain(registry: string): string | null {
  return REGISTRY_DOMAIN[registry] ?? null;
}

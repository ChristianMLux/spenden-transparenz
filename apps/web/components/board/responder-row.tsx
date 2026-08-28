import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import type { Locale } from "@/i18n/routing";
import { DonationLine } from "@/components/donation/donation-line";
import { formatDate } from "@/lib/format";
import { donationView } from "@/lib/donation";
import type { Responder } from "@/lib/types";
import { Statement } from "./statement";

/** ISO 3166-1 region names from the platform, not a hand-maintained table. */
function countryName(code: string, locale: Locale): string {
  try {
    return new Intl.DisplayNames([locale], { type: "region" }).of(code) ?? code;
  } catch {
    return code;
  }
}

/**
 * One record of Tab A, in the dossier's two-column layout: identity on the left (the
 * record's "label line" is the org type, sitting above the name the way every other
 * panel in this variant carries a muted word above its heading), the reaction on the
 * right. Server-rendered for the same reason as Statement: <Datum> needs next-intl
 * translations, which only exist on the server in this app.
 *
 * The rule that drives this file: an organisation with no statement gets the identical
 * <article> frame, the same heading size and the same vertical presence as one with
 * three. There is no branch here that changes the wrapper, only the content inside it.
 */
export function ResponderRow({ responder, generatedAt }: { responder: Responder; generatedAt: string }) {
  const t = useTranslations("board");
  const tCommon = useTranslations("common");
  const locale = useLocale() as Locale;
  const headingId = `org-${(responder.org_id ?? responder.org_name_raw).replace(/[^a-zA-Z0-9_-]/g, "-")}`;

  return (
    <article aria-labelledby={headingId} className="dossier-record">
      <div className="md:grid md:grid-cols-[16rem_1fr] md:gap-6">
        <div className="min-w-0">
          <p className="dossier-panel-label">{tCommon(`orgType.${responder.org_type}`)}</p>
          <h2 id={headingId} className="text-lg">
            {responder.name}
          </h2>
          <p className="mt-1 text-xs text-muted">{countryName(responder.hq_country, locale)}</p>
          {responder.aliases.length > 0 && (
            <p className="mt-1 text-xs text-muted">{responder.aliases.join(" · ")}</p>
          )}
        </div>

        <div className="mt-3 min-w-0 md:mt-0">
          {responder.statements.length > 0 ? (
            <div className="space-y-3">
              {responder.statements.map((statement, i) => (
                <div key={statement.id}>
                  {i > 0 && <hr className="mb-3 border-dashed border-rule" />}
                  <Statement statement={statement} />
                </div>
              ))}
            </div>
          ) : (
            <div>
              <p className="max-w-[68ch] text-base text-ink">
                {t("empty.heading", { date: formatDate(generatedAt.slice(0, 10), locale) })}
              </p>
              <p className="mt-1 max-w-[68ch] text-sm text-ink">
                {t("empty.searchedLabel")} {t("empty.searchedText")}
              </p>
            </div>
          )}

          {/* The official donation channel, one line, same weight whether found or not
              (DonationLine mirrors ProvenanceLine's own found/not-found parity rule).
              Administrative information, not part of the reaction above it, so it gets
              its own dashed rule the way a second statement would. */}
          <div className="mt-3 border-t border-dashed border-rule pt-3">
            <DonationLine view={donationView(responder.donation)} />
          </div>

          {responder.org_id && (
            <p className="mt-3">
              {/* next/link's Link, not @/i18n/navigation's wrapped one: SiteFooter (every
                  page's layout) already pays for Link's own runtime and for next-intl's
                  pathname-translation chunk, so reusing plain next/link here with a
                  manually built, locale-invariant href (the org route is identical in
                  both locales, see routing.ts) adds nothing beyond what the shell
                  already ships, while a raw <a> would have given up prefetching for no
                  bundle benefit. */}
              <Link
                href={`/${locale}/organisation/${responder.org_id}`}
                className="text-sm text-accent underline-offset-2 hover:underline"
              >
                {t("viewOrg")}
              </Link>
            </p>
          )}
        </div>
      </div>
    </article>
  );
}

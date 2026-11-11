"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { ChangeValue } from "@/components/market/ChangeValue";
import { Badge } from "@/components/ui/badge";
import { api, type CompanyProfile } from "@/lib/api";
import { formatDateTime, formatMarketCap, formatNumber, formatPrice } from "@/lib/format";

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="tabular-nums">{children}</div>
    </div>
  );
}

export function CompanyHeader({ company }: { company: CompanyProfile }) {
  const quote = useQuery({
    queryKey: ["quote", company.ticker],
    queryFn: () => api.quote(company.ticker),
    refetchInterval: 60_000,
  });
  const price = quote.data?.price ?? company.price;
  const chg1d = quote.data?.chg_1d_pct ?? company.chg_1d_pct;
  const chg1dAbs = quote.data?.chg_1d_abs ?? company.chg_1d_abs;
  const sectorHref = company.sector ? `/?sector=${encodeURIComponent(company.sector)}` : "/";
  const industryHref =
    company.sector && company.industry
      ? `/?sector=${encodeURIComponent(company.sector)}&industry=${encodeURIComponent(company.industry)}`
      : sectorHref;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight">{company.name}</h1>
            <span className="text-xl text-muted-foreground">{company.ticker}</span>
            {company.in_sp500 && <Badge variant="outline">S&amp;P 500</Badge>}
            {company.in_ndx100 && <Badge variant="outline">Nasdaq-100</Badge>}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">
            <Link href={sectorHref} className="hover:underline">
              {company.sector ?? "Unclassified"}
            </Link>
            {company.industry && (
              <>
                {" › "}
                <Link href={industryHref} className="hover:underline">
                  {company.industry}
                </Link>
              </>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-semibold tabular-nums" data-testid="live-price">
            {formatPrice(price)}
          </div>
          <div className="flex items-center justify-end gap-2 text-sm">
            <ChangeValue value={chg1dAbs} mode="abs" />
            <ChangeValue value={chg1d} />
          </div>
          <div className="text-xs text-muted-foreground">
            {quote.data?.source === "finnhub" ? "Real-time (Finnhub)" : "Delayed (Yahoo)"} ·{" "}
            {formatDateTime(quote.data?.as_of ?? company.as_of)}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 rounded-xl border border-border p-4 text-sm sm:grid-cols-4 lg:grid-cols-7">
        <Stat label="Market cap">{formatMarketCap(company.market_cap)}</Stat>
        <Stat label="P/E">{formatNumber(company.pe_ratio, 1)}</Stat>
        <Stat label="1W">
          <ChangeValue value={company.chg_1w_pct} />
        </Stat>
        <Stat label="YTD">
          <ChangeValue value={company.chg_ytd_pct} />
        </Stat>
        <Stat label="52W low">{formatPrice(company.week52_low)}</Stat>
        <Stat label="52W high">{formatPrice(company.week52_high)}</Stat>
        <Stat label="Volume">{formatNumber(company.volume, 0)}</Stat>
      </div>
    </section>
  );
}

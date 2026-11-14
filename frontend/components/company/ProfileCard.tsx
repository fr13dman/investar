import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CompanyProfile } from "@/lib/api";
import { formatCompact, formatNumber } from "@/lib/format";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-border/50 py-1.5 text-sm last:border-0">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right">{children ?? "—"}</dd>
    </div>
  );
}

export function ProfileCard({ company }: { company: CompanyProfile }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>About {company.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {company.description ?? "No company description available yet."}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Company facts</CardTitle>
        </CardHeader>
        <CardContent>
          <dl>
            <Row label="Headquarters">{company.headquarters}</Row>
            <Row label="Employees">{company.employees ? formatNumber(company.employees, 0) : null}</Row>
            <Row label="Founded">{company.founded}</Row>
            <Row label="Exchange">{company.exchange}</Row>
            <Row label="GICS sector">{company.gics_sector}</Row>
            <Row label="GICS sub-industry">{company.gics_sub_industry}</Row>
            <Row label="SEC CIK">{company.cik}</Row>
            <Row label="Website">
              {company.website ? (
                <a href={company.website} target="_blank" rel="noopener noreferrer" className="hover:underline">
                  {company.website.replace(/^https?:\/\/(www\.)?/, "")}
                </a>
              ) : null}
            </Row>
          </dl>
        </CardContent>
      </Card>
      {company.executives.length > 0 && (
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Leadership</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
              {company.executives.map((e) => (
                <li key={`${e.name}-${e.title}`} className="rounded-lg border border-border p-2">
                  <div className="font-medium">
                    {e.name} {e.is_ceo && <span className="text-xs text-amber-600 dark:text-amber-400">CEO</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">{e.title}</div>
                  {e.total_pay ? <div className="text-xs text-muted-foreground">Pay {formatCompact(e.total_pay, "$")}</div> : null}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

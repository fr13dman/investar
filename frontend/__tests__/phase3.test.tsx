import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { fillFor, GlobalPresencePanel } from "@/components/company/GlobalPresencePanel";
import { PatentsPanel } from "@/components/company/PatentsPanel";
import type { GlobalPresence, Patents } from "@/lib/api";

import { mockFetch, renderWithQuery } from "./helpers";

vi.mock("react-simple-maps", () => ({
  ComposableMap: ({ children }: { children: React.ReactNode }) => <svg aria-label="Subsidiary countries map">{children}</svg>,
  Geographies: ({ children }: { children: (p: { geographies: unknown[] }) => React.ReactNode }) => (
    <g>{children({ geographies: [{ rsmKey: "g1", id: "372", properties: { name: "Ireland" } }, { rsmKey: "g2", id: "250", properties: { name: "France" } }] })}</g>
  ),
  Geography: ({ children, fill, ...rest }: { children: React.ReactNode; fill: string; "data-country"?: string }) => (
    <path data-testid="geo" data-fill={fill} data-country={rest["data-country"]}>{children}</path>
  ),
}));

const fresh = { fetched_at: "2026-11-10T12:00:00", status: "ok", message: null, refreshing: false };

const globalData: GlobalPresence = {
  subsidiaries: [
    { name: "Apple Operations International Limited", jurisdiction: "Ireland", country_name: "Ireland", country_alpha2: "IE" },
    { name: "Apple Distribution International Limited", jurisdiction: "Ireland", country_name: "Ireland", country_alpha2: "IE" },
    { name: "Apple Asia Limited", jurisdiction: "Hong Kong", country_name: "Hong Kong", country_alpha2: "HK" },
  ],
  countries: [
    { country_name: "Ireland", alpha2: "IE", numeric: "372", count: 2 },
    { country_name: "Hong Kong", alpha2: "HK", numeric: "344", count: 1 },
  ],
  unmapped: 0,
  revenue_by_region: [
    { axis: "geographic", period_end: "2026-09-26", total: 478.8e9, regions: [
      { region: "Other Countries", member: "aapl:OtherCountriesMember", revenue: 228.7e9, country_alpha2: null, share_pct: 47.8 },
      { region: "United States", member: "country:US", revenue: 167.7e9, country_alpha2: "US", share_pct: 35.0 },
    ] },
    { axis: "segment", period_end: "2026-09-26", total: 478.8e9, regions: [
      { region: "Americas", member: "aapl:AmericasSegmentMember", revenue: 198.1e9, country_alpha2: null, share_pct: 41.4 },
    ] },
  ],
  filing: { accession: "0000320193-26-000026", url: "https://www.sec.gov/x-index.htm" },
  refresh: fresh,
};

const patentsData: Patents = {
  granted: {
    total_10y: 25_000,
    by_year: [{ year: "2025", count: 2500 }, { year: "2026", count: 2600 }],
    top_cpc: { items: [{ code: "G06F", title: "Electric digital data processing", count: 80 }], note: "based on the 1000 most recent grants" },
    recent: [{ number: "12000001", title: "Foldable display", abstract: "A display that folds.", date: "2026-10-01", cpc_class: "G06F", cpc_title: "Electric digital data processing", assignee: "Apple Inc.", url: "https://patents.google.com/patent/US12000001", source: "patentsview_api" }],
  },
  applications: {
    total_24m: 4321,
    top_cpc: { items: [], note: null },
    recent: [{ number: "20260123456", title: "Smart ring", abstract: null, date: "2026-09-03", cpc_class: null, cpc_title: null, assignee: null, url: "https://patents.google.com/patent/US20260123456A1", source: "patentsview_api" }],
  },
  assignees: [{ assignee_name: "Apple Inc.", match: "exact", source: "curated" }],
  source: "patentsview_api",
  refresh: fresh,
};

describe("GlobalPresencePanel", () => {
  it("colors subsidiary countries, lists counts and revenue by region", async () => {
    mockFetch({ "/api/companies/AAPL/global": globalData });
    renderWithQuery(<GlobalPresencePanel ticker="AAPL" />);
    expect(await screen.findByText("Subsidiaries in 2 countries")).toBeInTheDocument();
    const paths = screen.getAllByTestId("geo");
    expect(paths.find((p) => p.dataset.country === "IE")!.dataset.fill).toContain("rgba(52, 211, 153");
    expect(paths.find((p) => !p.dataset.country)!.dataset.fill).toBe("rgba(255,255,255,0.06)");
    const byCountry = screen.getByRole("list", { name: "Subsidiaries by country" });
    expect(within(byCountry).getByText("(not on map)")).toBeInTheDocument();

    const table = screen.getByRole("table", { name: "Revenue by region" });
    expect(within(table).getByText("47.8%")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Geographic segments" }));
    expect(within(screen.getByRole("table", { name: "Revenue by region" })).getByText("Americas")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Filter subsidiaries"), { target: { value: "asia" } });
    expect(within(screen.getByRole("list", { name: "Subsidiaries" })).getAllByRole("listitem")).toHaveLength(1);
  });

  it("explains when revenue by geography is not reported", async () => {
    mockFetch({ "/api/companies/AAPL/global": { ...globalData, revenue_by_region: [] } });
    renderWithQuery(<GlobalPresencePanel ticker="AAPL" />);
    expect(await screen.findByText(/Not reported/)).toBeInTheDocument();
  });

  it("shows a loading message instead of 'Not reported' during the first fetch", async () => {
    mockFetch({
      "/api/companies/AAPL/global": {
        ...globalData, subsidiaries: [], countries: [], revenue_by_region: [],
        refresh: { fetched_at: null, status: null, message: null, refreshing: true },
      },
    });
    renderWithQuery(<GlobalPresencePanel ticker="AAPL" />);
    expect(await screen.findAllByText("Reading the latest 10-K…")).toHaveLength(2);
    expect(screen.queryByText(/Not reported/)).not.toBeInTheDocument();
  });

  it("scales fill intensity", () => {
    expect(fillFor(0, 5)).toBe("rgba(255,255,255,0.06)");
    expect(fillFor(5, 5)).toBe("rgba(52, 211, 153, 1.00)");
  });
});

describe("PatentsPanel", () => {
  it("shows totals, lists and edits assignee names", async () => {
    const fetchSpy = mockFetch({
      "/api/companies/AAPL/patent-assignees": {
        assignees: [{ assignee_name: "Apple Inc.", match: "exact", source: "manual" }, { assignee_name: "Beats Electronics", match: "prefix", source: "manual" }],
        refresh: { ...fresh, refreshing: true },
      },
      "/api/companies/AAPL/patents": patentsData,
    });
    renderWithQuery(<PatentsPanel ticker="AAPL" />);
    await waitFor(() => expect(screen.getByTestId("granted-total")).toHaveTextContent("25,000"));
    expect(screen.getByTestId("applications-total")).toHaveTextContent("4,321");
    expect(within(screen.getByRole("list", { name: "Granted patents" })).getByRole("link", { name: "Foldable display" })).toHaveAttribute(
      "href",
      "https://patents.google.com/patent/US12000001",
    );
    expect(within(screen.getByRole("list", { name: "Pending applications" })).getByText("Smart ring")).toBeInTheDocument();
    expect(screen.getByText(/based on the 1000 most recent grants/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Assignee name"), { target: { value: "Beats Electronics" } });
    fireEvent.change(screen.getByLabelText("Match type"), { target: { value: "prefix" } });
    fireEvent.click(screen.getByRole("button", { name: "Add name" }));
    await waitFor(() => expect(within(screen.getByRole("list", { name: "Patent assignee names" })).getByText("Beats Electronics")).toBeInTheDocument());
    const put = fetchSpy.mock.calls.find(([, init]) => init?.method === "PUT")!;
    expect(JSON.parse(String(put[1]!.body))).toEqual([
      { assignee_name: "Apple Inc.", match: "exact" },
      { assignee_name: "Beats Electronics", match: "prefix" },
    ]);
  });

  it("surfaces the API-unavailable message with the bulk import hint", async () => {
    mockFetch({
      "/api/companies/AAPL/patents": {
        ...patentsData,
        granted: { total_10y: null, by_year: [], top_cpc: { items: [], note: null }, recent: [] },
        applications: { total_24m: null, top_cpc: { items: [], note: null }, recent: [] },
        refresh: { ...fresh, status: "error", message: "PatentsView API unreachable; use `investar import-patents-bulk` instead" },
      },
    });
    renderWithQuery(<PatentsPanel ticker="AAPL" />);
    expect(await screen.findByRole("status")).toHaveTextContent("import-patents-bulk");
  });
});

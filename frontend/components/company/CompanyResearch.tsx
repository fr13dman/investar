"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";

import { CeoScorecardPanel } from "./CeoScorecardPanel";
import { CompanyHeader } from "./CompanyHeader";
import { GlobalPresencePanel } from "./GlobalPresencePanel";
import { NewsPanel } from "./NewsPanel";
import { PatentsPanel } from "./PatentsPanel";
import { PriceChart } from "./PriceChart";
import { ProfileCard } from "./ProfileCard";
import { RefreshNote, pollWhileRefreshing } from "./RefreshNote";

export function CompanyResearch({ ticker }: { ticker: string }) {
  const { data, error, isLoading } = useQuery({
    queryKey: ["company", ticker],
    queryFn: () => api.company(ticker),
    refetchInterval: pollWhileRefreshing,
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading {ticker}…</p>;
  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Unknown ticker {ticker}</h1>
        <p className="text-sm text-muted-foreground">
          Investar covers S&amp;P 500 and Nasdaq-100 companies. <Link href="/" className="underline">Back to the screener</Link>
        </p>
      </div>
    );
  }
  if (!data) return <p role="alert" className="text-sm text-rose-400">Could not load {ticker}.</p>;

  return (
    <div className="space-y-6">
      <CompanyHeader company={data} />
      <PriceChart ticker={data.ticker} />
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="ceo">CEO performance</TabsTrigger>
          <TabsTrigger value="news">News</TabsTrigger>
          <TabsTrigger value="global">Global presence</TabsTrigger>
          <TabsTrigger value="patents">Patents</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="space-y-3 pt-4">
          <RefreshNote source="Yahoo Finance profile" status={data.refresh} />
          <ProfileCard company={data} />
        </TabsContent>
        <TabsContent value="ceo" className="pt-4">
          <CeoScorecardPanel ticker={data.ticker} />
        </TabsContent>
        <TabsContent value="news" className="pt-4">
          <NewsPanel ticker={data.ticker} />
        </TabsContent>
        <TabsContent value="global" className="pt-4">
          <GlobalPresencePanel ticker={data.ticker} />
        </TabsContent>
        <TabsContent value="patents" className="pt-4">
          <PatentsPanel ticker={data.ticker} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

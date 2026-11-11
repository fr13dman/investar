import { CompanyResearch } from "@/components/company/CompanyResearch";

export default async function CompanyPage({ params }: PageProps<"/company/[ticker]">) {
  const { ticker } = await params;
  return <CompanyResearch ticker={decodeURIComponent(ticker).toUpperCase()} />;
}

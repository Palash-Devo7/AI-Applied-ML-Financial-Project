import CompanyView from "./company-view";

interface Props {
  params: Promise<{ ticker: string }>;
}

export default async function CompanyPage({ params }: Props) {
  const { ticker } = await params;
  return <CompanyView ticker={ticker} />;
}

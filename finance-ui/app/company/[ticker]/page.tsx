import { AuthGuard } from "@/components/auth-guard";
import CompanyView from "./company-view";

interface Props {
  params: Promise<{ ticker: string }>;
}

export default async function CompanyPage({ params }: Props) {
  const { ticker } = await params;
  return (
    <AuthGuard>
      <CompanyView ticker={ticker} />
    </AuthGuard>
  );
}

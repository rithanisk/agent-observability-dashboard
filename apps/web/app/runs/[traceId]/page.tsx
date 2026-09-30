import { TraceDetail } from "@/components/trace-detail";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ traceId: string }>;
}) {
  const { traceId } = await params;
  return <TraceDetail traceId={traceId} />;
}

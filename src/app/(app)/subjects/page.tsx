import Catalog from "@/components/Catalog";

export default async function SubjectsPage({ searchParams }: { searchParams: Promise<{ archived?: string }> }) {
  const { archived } = await searchParams;
  return <Catalog kind="subject" showArchived={archived === "1"} />;
}

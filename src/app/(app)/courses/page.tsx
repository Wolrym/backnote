import Catalog from "@/components/Catalog";

export default async function CoursesPage({ searchParams }: { searchParams: Promise<{ archived?: string }> }) {
  const { archived } = await searchParams;
  return <Catalog kind="course" showArchived={archived === "1"} />;
}

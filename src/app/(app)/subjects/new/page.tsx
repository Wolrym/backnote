import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { redirect } from "next/navigation";
import SubjectForm from "../SubjectForm";

export default async function NewSubjectPage({ searchParams }: { searchParams: Promise<{ kind?: string }> }) {
  const me = await requireUser();
  if (!me.canEdit) redirect("/subjects");
  const { kind } = await searchParams;
  const k = kind === "course" ? "course" : "subject";
  return (
    <div>
      <PageHeader title={k === "course" ? "Новий курс" : "Новий предмет"} />
      <SubjectForm kind={k} />
    </div>
  );
}

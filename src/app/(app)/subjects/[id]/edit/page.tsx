import { notFound, redirect } from "next/navigation";
import { PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { getSubject } from "@/lib/data";
import SubjectForm from "../../SubjectForm";

export default async function EditSubjectPage({ params }: { params: Promise<{ id: string }> }) {
  const me = await requireUser();
  const { id } = await params;
  if (!me.canEdit) redirect(`/subjects/${id}`);
  const subject = await getSubject(Number(id));
  if (!subject) notFound();
  return (
    <div>
      <PageHeader title="Редагування" subtitle={subject.title} />
      <SubjectForm subject={subject} kind={subject.kind === "course" ? "course" : "subject"} />
    </div>
  );
}

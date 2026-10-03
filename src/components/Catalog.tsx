import { Plus } from "lucide-react";
import { LinkButton, PageHeader } from "@/components/ui";
import { requireUser } from "@/lib/auth";
import { listSubjects } from "@/lib/data";
import CatalogView from "./CatalogView";

export default async function Catalog({
  kind,
  showArchived,
}: {
  kind: "subject" | "course";
  showArchived: boolean;
}) {
  const me = await requireUser();
  const all = await listSubjects(me.id, kind);
  const archivedCount = all.filter((s) => s.isArchived).length;
  const list = all.filter((s) => s.isArchived === showArchived);

  return (
    <div className="w-full space-y-6">
      <PageHeader
        title={kind === "subject" ? "Предмети" : "Курси"}
        subtitle={
          kind === "subject"
            ? "Університетські предмети за навчальними курсами та семестрами"
            : "Онлайн-курси та додаткові навчальні треки"
        }
        action={
          me.canEdit && (
            <LinkButton href={`/subjects/new?kind=${kind}`} variant="primary">
              <Plus size={16} /> Додати
            </LinkButton>
          )
        }
      />

      <CatalogView
        items={list}
        kind={kind}
        showArchived={showArchived}
        archivedCount={archivedCount}
      />
    </div>
  );
}

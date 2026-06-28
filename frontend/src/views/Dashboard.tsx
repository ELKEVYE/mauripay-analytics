import { DatasetFilter } from "../components/DatasetFilter";

type DashboardProps = {
  datasetPath: string;
  loading: boolean;
  selectedFile: File | null;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
};

export function Dashboard({
  datasetPath,
  loading,
  selectedFile,
  onFileChange,
  onSubmit,
}: DashboardProps) {
  return (
    <section className="space-y-4" aria-label="Chargement du dataset">
      <DatasetFilter
        datasetPath={datasetPath}
        loading={loading}
        selectedFile={selectedFile}
        onFileChange={onFileChange}
        onSubmit={onSubmit}
      />
    </section>
  );
}

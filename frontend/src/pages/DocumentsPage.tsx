import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import Sidebar from "../components/layout/Sidebar";
import ActionBar from "../components/documents/ActionBar";
import DeleteConfirmModal from "../components/documents/DeleteConfirmModal";
import DocumentCard from "../components/documents/DocumentCard";
import EmptyDocumentsState from "../components/documents/EmptyDocumentsState";
import UploadModal from "../components/documents/UploadModal";
import ViewAnalysisModal from "../components/documents/ViewAnalysisModal";
import { documentsApi } from "../services/api";
import type { DocumentItem } from "../types";

export interface FeedbackBanner {
  type: "success" | "error";
  message: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Selection state (supports single & multi-selection)
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Modal states
  const [pendingUploadFile, setPendingUploadFile] = useState<File | null>(null);
  const [previewDocument, setPreviewDocument] = useState<DocumentItem | null>(
    null
  );
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);

  // Drag-and-drop state when grid already has documents
  const [isDraggingOverGrid, setIsDraggingOverGrid] = useState<boolean>(false);

  // Toast / Feedback notifications (Page 7 Differential)
  const [feedback, setFeedback] = useState<FeedbackBanner | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showFeedback = useCallback(
    (type: "success" | "error", message: string) => {
      setFeedback({ type, message });
    },
    []
  );

  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(null), 5000);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await documentsApi.list();
      setDocuments(response.items);
      setSelectedIds((prev) =>
        prev.filter((id) => response.items.some((doc) => doc.id === id))
      );
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Não foi possível carregar seus documentos.";
      setLoadError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchDocuments();
  }, [fetchDocuments]);

  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  }, []);

  const handleTriggerFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setPendingUploadFile(file);
    }
    e.target.value = "";
  };

  const handleFileDrop = useCallback((file: File) => {
    setPendingUploadFile(file);
  }, []);

  const handleUploadSuccess = useCallback(
    (created: DocumentItem) => {
      setPendingUploadFile(null);
      setDocuments((prev) => [created, ...prev]);

      if (created.status === "COMPLETED") {
        showFeedback(
          "success",
          "Documento enviado e analisado pela IA com sucesso!"
        );
      } else {
        showFeedback(
          "error",
          "Arquivo salvo na AWS, mas a análise da IA falhou. Clique no documento para tentar novamente."
        );
      }

      // Open the preview modal immediately so the user sees the AI result (or Retry option)
      setPreviewDocument(created);
    },
    [showFeedback]
  );

  const handleDocumentUpdated = useCallback(
    (updated: DocumentItem) => {
      setDocuments((prev) =>
        prev.map((doc) => (doc.id === updated.id ? updated : doc))
      );
      if (updated.status === "COMPLETED") {
        showFeedback("success", "Análise da IA concluída com sucesso!");
      }
    },
    [showFeedback]
  );

  const handleViewSelectedAnalysis = useCallback(() => {
    if (selectedIds.length !== 1) return;
    const found = documents.find((d) => d.id === selectedIds[0]);
    if (found) {
      setPreviewDocument(found);
    }
  }, [documents, selectedIds]);

  const handleConfirmDelete = useCallback(async () => {
    if (selectedIds.length === 0) return;
    try {
      const result =
        selectedIds.length === 1
          ? await documentsApi.deleteOne(selectedIds[0])
          : await documentsApi.bulkDelete(selectedIds);

      const deletedSet = new Set(result.deleted_ids);
      setDocuments((prev) => prev.filter((doc) => !deletedSet.has(doc.id)));
      setSelectedIds([]);
      setIsDeleteModalOpen(false);
      showFeedback(
        "success",
        result.deleted_count === 1
          ? "Documento excluído com sucesso."
          : `${result.deleted_count} documentos excluídos com sucesso.`
      );
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Erro ao excluir documento(s).";
      showFeedback("error", msg);
      setIsDeleteModalOpen(false);
    }
  }, [selectedIds, showFeedback]);

  const handleContainerDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (documents.length === 0) return;
    e.preventDefault();
    if (!isDraggingOverGrid) setIsDraggingOverGrid(true);
  };

  const handleContainerDragLeave = (e: DragEvent<HTMLDivElement>) => {
    if (documents.length === 0) return;
    e.preventDefault();
    setIsDraggingOverGrid(false);
  };

  const handleContainerDrop = (e: DragEvent<HTMLDivElement>) => {
    if (documents.length === 0) return;
    e.preventDefault();
    setIsDraggingOverGrid(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setPendingUploadFile(file);
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfcfd] flex flex-col md:flex-row w-full">
      <Sidebar />

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt,.md,.csv,.png,.jpg,.jpeg,.webp"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Main Content Area (Figma node 80:416 / 80:758) */}
      <main className="flex-1 flex flex-col gap-[24px] p-[16px] sm:p-[24px] min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-4 w-full">
          <h1 className="font-semibold text-[28px] sm:text-[32px] leading-[40px] text-[#1c2024]">
            Documentos
          </h1>

          {/* Toast / Feedback Notification Banner */}
          {feedback && (
            <div
              role="status"
              className={`flex items-center gap-2.5 px-4 py-2.5 rounded-[8px] border text-sm font-medium shadow-sm transition-all ${
                feedback.type === "success"
                  ? "bg-[#30a46c]/10 border-[#30a46c]/30 text-[#1c2024]"
                  : "bg-[#e5484d]/10 border-[#e5484d]/30 text-[#e5484d]"
              }`}
            >
              {feedback.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 text-[#30a46c] shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-[#e5484d] shrink-0" />
              )}
              <span>{feedback.message}</span>
            </div>
          )}
        </div>

        {/* White Container Card (Figma node 80:419 / 80:761) */}
        <div
          onDragOver={handleContainerDragOver}
          onDragLeave={handleContainerDragLeave}
          onDrop={handleContainerDrop}
          className={`bg-white border rounded-[12px] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] flex-1 flex flex-col gap-[16px] pt-[16px] pb-[24px] px-[16px] sm:px-[24px] min-h-[540px] relative transition-colors ${
            isDraggingOverGrid
              ? "border-[#30a46c] border-dashed bg-[#30a46c]/[0.02]"
              : "border-[#d9d9e0]"
          }`}
        >
          <ActionBar
            totalCount={documents.length}
            selectedCount={selectedIds.length}
            onAddClick={handleTriggerFilePicker}
            onViewSelectedAnalysis={handleViewSelectedAnalysis}
            onDeleteSelected={() => setIsDeleteModalOpen(true)}
          />

          {/* Loading State */}
          {isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20">
              <Loader2 className="w-7 h-7 animate-spin text-[#30a46c]" />
              <p className="text-sm text-[#60646c]">
                Carregando seus documentos...
              </p>
            </div>
          ) : loadError ? (
            /* Error State with Retry */
            <div className="flex-1 flex flex-col items-center justify-center gap-3 py-20 text-center">
              <AlertCircle className="w-8 h-8 text-[#e5484d]" />
              <p className="text-sm font-medium text-[#1c2024]">{loadError}</p>
              <button
                type="button"
                onClick={() => void fetchDocuments()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-[8px] bg-[#f0f0f3] hover:bg-[#d9d9e0] text-xs font-medium text-[#1c2024] transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Tentar novamente
              </button>
            </div>
          ) : documents.length === 0 ? (
            /* Empty State (Figma node 80:422) */
            <EmptyDocumentsState
              onFileDrop={handleFileDrop}
              onBrowseClick={handleTriggerFilePicker}
            />
          ) : (
            /* Populated Documents Grid (Figma node 80:767) */
            <div className="flex flex-wrap gap-[8px] items-start content-start w-full pt-1">
              {documents.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  isSelected={selectedIds.includes(doc.id)}
                  onToggleSelect={handleToggleSelect}
                  onOpenPreview={(item) => setPreviewDocument(item)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* 1. Upload & AI Instruction Modal (Figma node 80:645) */}
      {pendingUploadFile && (
        <UploadModal
          file={pendingUploadFile}
          onClose={() => setPendingUploadFile(null)}
          onSuccess={handleUploadSuccess}
        />
      )}

      {/* 2. View AI Analysis Modal (Figma node 80:1302) */}
      {previewDocument && (
        <ViewAnalysisModal
          document={previewDocument}
          onClose={() => setPreviewDocument(null)}
          onDocumentUpdated={handleDocumentUpdated}
        />
      )}

      {/* 3. Safe Delete Confirmation Modal (Page 7 Differential) */}
      {isDeleteModalOpen && selectedIds.length > 0 && (
        <DeleteConfirmModal
          selectedCount={selectedIds.length}
          onClose={() => setIsDeleteModalOpen(false)}
          onConfirm={handleConfirmDelete}
        />
      )}
    </div>
  );
}

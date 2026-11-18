import { useEffect, useState } from "react";
import { AlertTriangle, ExternalLink, Loader2, RotateCcw } from "lucide-react";
import { documentsApi, formatFileSize } from "../../services/api";
import type { DocumentItem } from "../../types";
import closeXIcon from "../../assets/icons/close-x.svg";
import fileDocIcon from "../../assets/icons/file-doc.svg";

interface ViewAnalysisModalProps {
  document: DocumentItem;
  onClose: () => void;
  onDocumentUpdated: (updated: DocumentItem) => void;
}

export default function ViewAnalysisModal({
  document,
  onClose,
  onDocumentUpdated,
}: ViewAnalysisModalProps) {
  const [currentDoc, setCurrentDoc] = useState<DocumentItem>(document);
  const [isRetrying, setIsRetrying] = useState<boolean>(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const isImage = [".png", ".jpg", ".jpeg", ".webp"].includes(
    currentDoc.file_extension.toLowerCase()
  );

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !isRetrying) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isRetrying, onClose]);

  const handleRetryAnalysis = async () => {
    setIsRetrying(true);
    setRetryError(null);
    try {
      const updated = await documentsApi.retry(currentDoc.id);
      setCurrentDoc(updated);
      onDocumentUpdated(updated);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Não foi possível tentar novamente.";
      setRetryError(msg);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4"
      onClick={() => {
        if (!isRetrying) onClose();
      }}
    >
      {/* Dialog Box (Figma node 80:1302) */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="view-dialog-title"
        onClick={(e) => e.stopPropagation()}
        className="bg-[#fcfcfd] border border-[#d9d9e0] rounded-[12px] shadow-[0px_4px_8px_0px_rgba(0,0,0,0.04)] w-full max-w-[480px] flex flex-col overflow-hidden"
      >
        {/* Header (Figma node 80:1303) */}
        <div className="flex gap-[16px] items-center pb-[16px] pl-[16px] pr-[4px] pt-[4px] w-full">
          <h2
            id="view-dialog-title"
            className="flex-1 font-medium text-[#1c2024] text-[20px] leading-[20px] opacity-90 pt-[6px]"
          >
            Prévia do Documento
          </h2>
          <button
            type="button"
            disabled={isRetrying}
            onClick={onClose}
            aria-label="Fechar modal"
            className="flex items-center justify-center rounded-[12px] size-[32px] hover:bg-[#f0f0f3] transition-colors disabled:opacity-50"
          >
            <img alt="" className="size-[16px]" src={closeXIcon} />
          </button>
        </div>

        {/* Preview Area (Figma node 80:1306) */}
        <div className="flex items-center px-[8px] w-full">
          <div className="bg-[#f9f9fb] flex-1 flex flex-col items-center justify-center p-[16px] h-[128px] relative rounded-[12px] overflow-hidden">
            <div className="bg-white border border-[#d9d9e0] h-[96px] w-[67px] rounded-[4px] shrink-0 flex items-center justify-center overflow-hidden">
              {isImage && currentDoc.presigned_url ? (
                <img
                  src={currentDoc.presigned_url}
                  alt={currentDoc.title}
                  className="size-full object-cover"
                />
              ) : (
                <img alt="" className="size-[28px]" src={fileDocIcon} />
              )}
            </div>

            <div className="absolute bottom-[8px] left-[8px] flex font-medium gap-[4px] items-center text-[10px] leading-[10px] whitespace-nowrap">
              <span className="text-[#80838d]">
                {formatFileSize(currentDoc.file_size)}
              </span>
              <span className="text-[#d9d9e0]">•</span>
              <span className="text-[#80838d]">{currentDoc.file_extension}</span>
            </div>

            {currentDoc.presigned_url && (
              <a
                href={currentDoc.presigned_url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute bottom-[8px] right-[8px] inline-flex items-center gap-1 text-[10px] font-medium text-[#30a46c] hover:underline"
              >
                <span>Abrir original</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {/* Body (Figma node 80:1314) */}
        <div className="flex flex-col p-[16px] w-full">
          <div className="flex flex-col gap-[8px] w-full">
            {/* Title Display (Figma node 80:1316) */}
            <div className="flex flex-col gap-[4px] w-full">
              <span className="px-[14px] font-medium text-[#60646c] text-[14px] leading-[14px]">
                Título
              </span>
              <div className="bg-[#f0f0f3] h-[40px] flex items-center px-[16px] py-[8px] rounded-[8px] w-full overflow-hidden">
                <p
                  className="font-normal text-[#1c2024] text-[16px] leading-[24px] truncate"
                  title={currentDoc.title}
                >
                  {currentDoc.title}
                </p>
              </div>
            </div>

            {/* AI Analysis Display (Figma node 80:1341) */}
            <div className="flex flex-col gap-[4px] w-full">
              <span className="px-[14px] font-medium text-[#60646c] text-[14px] leading-[14px]">
                Analise da IA
              </span>

              {currentDoc.status === "FAILED" ? (
                <div className="bg-[#e5484d]/5 border border-[#e5484d]/30 rounded-[8px] p-[16px] flex flex-col gap-3">
                  <div className="flex items-start gap-2 text-xs text-[#e5484d]">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      {currentDoc.error_message ||
                        "Não foi possível concluir a análise da IA para este documento."}
                    </span>
                  </div>

                  {retryError && (
                    <p className="text-xs text-[#e5484d]">{retryError}</p>
                  )}

                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={isRetrying}
                      onClick={() => void handleRetryAnalysis()}
                      className="inline-flex items-center gap-1.5 bg-[#30a46c] hover:bg-[#29915e] text-[#fcfcfd] text-xs font-medium px-3 py-1.5 rounded-[8px] transition-colors disabled:opacity-60"
                    >
                      {isRetrying ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Analisando novamente...</span>
                        </>
                      ) : (
                        <>
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span>Tentar novamente</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-[#f0f0f3] min-h-[112px] max-h-[260px] overflow-y-auto px-[16px] py-[8px] rounded-[8px] w-full">
                  <p className="font-normal text-[#80838d] text-[16px] leading-[24px] whitespace-pre-wrap break-words">
                    {currentDoc.ai_response || "Sem resposta disponível."}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

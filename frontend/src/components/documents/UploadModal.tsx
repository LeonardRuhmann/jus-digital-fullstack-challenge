import { useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { documentsApi, formatFileSize } from "../../services/api";
import type { DocumentItem } from "../../types";
import closeXIcon from "../../assets/icons/close-x.svg";
import fileDocIcon from "../../assets/icons/file-doc.svg";

const ALLOWED_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".doc",
  ".txt",
  ".md",
  ".csv",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
];
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

interface UploadModalProps {
  file: File;
  onClose: () => void;
  onSuccess: (createdDocument: DocumentItem) => void;
}

export default function UploadModal({
  file,
  onClose,
  onSuccess,
}: UploadModalProps) {
  const [title, setTitle] = useState<string>(file.name);
  const [instruction, setInstruction] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const extension = useMemo(() => {
    const idx = file.name.lastIndexOf(".");
    return idx >= 0 ? file.name.slice(idx).toLowerCase() : "";
  }, [file.name]);

  const isImage = useMemo(
    () => [".png", ".jpg", ".jpeg", ".webp"].includes(extension),
    [extension]
  );

  const imagePreviewUrl = useMemo(() => {
    if (!isImage) return null;
    return URL.createObjectURL(file);
  }, [file, isImage]);

  useEffect(() => {
    return () => {
      if (imagePreviewUrl) {
        URL.revokeObjectURL(imagePreviewUrl);
      }
    };
  }, [imagePreviewUrl]);

  // Close on Escape key when not submitting
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !isSubmitting) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isSubmitting, onClose]);

  const validateBeforeSubmit = (): string | null => {
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return `Formato '${extension || "desconhecido"}' não suportado. Envie ${ALLOWED_EXTENSIONS.join(", ")}.`;
    }
    if (file.size === 0) {
      return "O arquivo selecionado está vazio.";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return "O arquivo excede o tamanho máximo permitido de 10 MB.";
    }
    if (!title.trim()) {
      return "Preencha o título do documento.";
    }
    if (!instruction.trim()) {
      return "Preencha a instrução para a IA analisar o documento.";
    }
    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const validationError = validateBeforeSubmit();
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const created = await documentsApi.upload(
        file,
        title.trim(),
        instruction.trim()
      );
      onSuccess(created);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Erro ao enviar e analisar o documento.";
      setErrorMessage(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4"
      onClick={() => {
        if (!isSubmitting) onClose();
      }}
    >
      {/* Dialog Box (Figma node 80:645) */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-dialog-title"
        onClick={(e) => e.stopPropagation()}
        className="bg-[#fcfcfd] border border-[#d9d9e0] rounded-[12px] shadow-[0px_4px_8px_0px_rgba(0,0,0,0.04)] w-full max-w-[480px] flex flex-col overflow-hidden"
      >
        {/* Header (Figma node 80:646) */}
        <div className="flex gap-[16px] items-center pb-[16px] pl-[16px] pr-[4px] pt-[4px] w-full">
          <h2
            id="upload-dialog-title"
            className="flex-1 font-medium text-[#1c2024] text-[20px] leading-[20px] opacity-90 pt-[6px]"
          >
            Prévia do Documento
          </h2>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            aria-label="Fechar modal"
            className="flex items-center justify-center rounded-[12px] size-[32px] hover:bg-[#f0f0f3] transition-colors disabled:opacity-50"
          >
            <img alt="" className="size-[16px]" src={closeXIcon} />
          </button>
        </div>

        {/* Preview Area (Figma node 80:649) */}
        <div className="flex items-center px-[8px] w-full">
          <div className="bg-[#f9f9fb] flex-1 flex flex-col items-center justify-center p-[16px] h-[128px] relative rounded-[12px] overflow-hidden">
            <div className="bg-white border border-[#d9d9e0] h-[96px] w-[67px] rounded-[4px] shrink-0 flex items-center justify-center overflow-hidden">
              {imagePreviewUrl ? (
                <img
                  src={imagePreviewUrl}
                  alt={file.name}
                  className="size-full object-cover"
                />
              ) : (
                <img alt="" className="size-[28px]" src={fileDocIcon} />
              )}
            </div>

            <div className="absolute bottom-[8px] left-[8px] flex font-medium gap-[4px] items-center text-[10px] leading-[10px] whitespace-nowrap">
              <span className="text-[#80838d]">
                {formatFileSize(file.size)}
              </span>
              <span className="text-[#d9d9e0]">•</span>
              <span className="text-[#80838d]">{extension || ".arq"}</span>
            </div>
          </div>
        </div>

        {/* Form Body (Figma node 80:657) */}
        <form
          onSubmit={(e) => void handleSubmit(e)}
          className="flex flex-col gap-[16px] p-[16px] w-full"
        >
          <div className="flex flex-col gap-[8px] w-full">
            {/* Title Input (Figma node 80:659) */}
            <div className="flex flex-col gap-[4px] w-full">
              <label
                htmlFor="doc-title-input"
                className="px-[14px] font-medium text-[#60646c] text-[14px] leading-[14px]"
              >
                Título
              </label>
              <input
                id="doc-title-input"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isSubmitting}
                maxLength={255}
                placeholder="Nome do documento"
                className="bg-[#f0f0f3] h-[40px] px-[16px] py-[8px] rounded-[8px] font-normal text-[#1c2024] text-[16px] leading-[24px] w-full focus:outline-none focus:ring-2 focus:ring-[#30a46c]/40 disabled:opacity-60"
              />
            </div>

            {/* AI Instruction Input (Figma node 80:660) */}
            <div className="flex flex-col gap-[4px] w-full">
              <label
                htmlFor="doc-instruction-input"
                className="px-[14px] font-medium text-[#60646c] text-[14px] leading-[14px]"
              >
                Instrução para IA
              </label>
              <textarea
                id="doc-instruction-input"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                disabled={isSubmitting}
                rows={2}
                maxLength={5000}
                placeholder="Como a IA deve analisar este documento"
                className="bg-[#f0f0f3] min-h-[64px] px-[16px] py-[8px] rounded-[8px] font-normal text-[#1c2024] placeholder:text-[#80838d] text-[16px] leading-[24px] w-full resize-none focus:outline-none focus:ring-2 focus:ring-[#30a46c]/40 disabled:opacity-60"
              />
            </div>
          </div>

          {/* Validation / Upload Error */}
          {errorMessage && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-[8px] border border-[#e5484d]/30 bg-[#e5484d]/5 px-3 py-2 text-xs text-[#e5484d]"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Loading Indicator During GPT-4o-mini Analysis (Page 7 Differential) */}
          {isSubmitting && (
            <div className="flex items-center gap-2.5 rounded-[8px] bg-[#30a46c]/10 px-3.5 py-2.5 text-xs font-medium text-[#1c2024]">
              <Loader2 className="w-4 h-4 animate-spin text-[#30a46c] shrink-0" />
              <span>
                Salvando no AWS S3 e analisando documento com GPT-4o-mini...
              </span>
            </div>
          )}

          {/* Footer Actions (Figma node 80:661) */}
          <div className="flex items-center justify-end w-full">
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-[#30a46c] hover:bg-[#29915e] flex items-center justify-center gap-2 px-[16px] py-[4px] h-[32px] rounded-[8px] font-medium text-[#fcfcfd] text-[16px] leading-[24px] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{isSubmitting ? "Analisando..." : "Salvar"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

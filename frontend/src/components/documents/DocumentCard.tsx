import { AlertTriangle, Loader2 } from "lucide-react";
import type { DocumentItem } from "../../types";
import { formatDateBR, formatFileSize } from "../../services/api";
import fileDocIcon from "../../assets/icons/file-doc.svg";
import checkIcon from "../../assets/icons/check.svg";

interface DocumentCardProps {
  document: DocumentItem;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
  onOpenPreview: (document: DocumentItem) => void;
}

export default function DocumentCard({
  document,
  isSelected,
  onToggleSelect,
  onOpenPreview,
}: DocumentCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onToggleSelect(document.id)}
      onDoubleClick={() => onOpenPreview(document)}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          onOpenPreview(document);
        } else if (e.key === " ") {
          e.preventDefault();
          onToggleSelect(document.id);
        }
      }}
      title={`${document.title} (Clique para selecionar, duplo clique para abrir análise)`}
      className={`group flex flex-col gap-[8px] h-[140px] w-[117.5px] items-center justify-center px-[6px] py-[4px] relative rounded-[8px] cursor-pointer select-none transition-colors ${
        isSelected
          ? "bg-[#e6f4fe]"
          : "bg-transparent hover:bg-[#f6f6f6]"
      }`}
    >
      {/* Top-left Selection Badge (Figma node I80:878;40:2571) */}
      {isSelected ? (
        <div
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect(document.id);
          }}
          className="absolute left-[6px] top-[6px] bg-[#0090ff] border border-[#0090ff] flex items-center justify-center p-[2px] rounded-[4px] z-10"
        >
          <img alt="Selecionado" className="size-[16px]" src={checkIcon} />
        </div>
      ) : (
        <div
          onClick={(e) => {
            e.stopPropagation();
            onToggleSelect(document.id);
          }}
          className="absolute left-[6px] top-[6px] size-[20px] rounded-[4px] border border-[#d9d9e0] bg-white opacity-0 group-hover:opacity-100 transition-opacity z-10"
        />
      )}

      {/* Status Indicator (Failed or Processing AI) */}
      {document.status === "FAILED" && (
        <div
          title={document.error_message || "Falha na análise da IA"}
          className="absolute right-[6px] top-[6px] bg-[#e5484d]/10 text-[#e5484d] p-1 rounded-[4px]"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
        </div>
      )}
      {document.status === "PROCESSING" && (
        <div
          title="Analisando com IA..."
          className="absolute right-[6px] top-[6px] bg-[#30a46c]/10 text-[#30a46c] p-1 rounded-[4px]"
        >
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        </div>
      )}

      {/* Paper Icon Box (Figma node 80:245) */}
      <div className="bg-white border border-[#d9d9e0] h-[64px] w-[45px] rounded-[4px] shrink-0 relative flex items-center justify-center overflow-hidden">
        <img alt="" className="size-[24px]" src={fileDocIcon} />
      </div>

      {/* Metadata: Title, Date, Size • Extension (Figma node 80:247) */}
      <div className="flex flex-col font-medium gap-[4px] items-center justify-center w-full min-w-0">
        <p className="text-[#1c2024] text-[12px] leading-[12px] text-center truncate w-full px-1">
          {document.title}
        </p>
        <p className="text-[#80838d] text-[10px] leading-[10px] text-center">
          {formatDateBR(document.created_at)}
        </p>
        <div className="flex gap-[4px] items-center text-[10px] leading-[10px] whitespace-nowrap">
          <span className="text-[#80838d]">
            {formatFileSize(document.file_size)}
          </span>
          <span className="text-[#d9d9e0]">•</span>
          <span className="text-[#80838d]">{document.file_extension}</span>
        </div>
      </div>
    </div>
  );
}

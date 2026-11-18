import { useState, type DragEvent } from "react";
import listMagnifyingGlassIcon from "../../assets/icons/list-magnifying-glass.svg";

interface EmptyDocumentsStateProps {
  onFileDrop: (file: File) => void;
  onBrowseClick: () => void;
}

export default function EmptyDocumentsState({
  onFileDrop,
  onBrowseClick,
}: EmptyDocumentsStateProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      onFileDrop(droppedFile);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={onBrowseClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onBrowseClick();
        }
      }}
      className={`border border-dashed rounded-[12px] flex-1 flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-colors min-h-[420px] ${
        isDragging
          ? "border-[#30a46c] bg-[#30a46c]/5"
          : "border-[#d9d9e0] hover:border-[#80838d]/60 hover:bg-[#f9f9fb]/50"
      }`}
    >
      <div className="flex flex-col gap-[8px] items-center max-w-[400px]">
        <div className="relative shrink-0 size-[56px]">
          <img
            alt=""
            className="block size-full"
            src={listMagnifyingGlassIcon}
          />
        </div>
        <div className="flex flex-col items-center">
          <p className="font-medium text-[20px] sm:text-[24px] leading-[32px] text-[#1c2024] opacity-90">
            {isDragging
              ? "Solte o arquivo aqui para enviar"
              : "Você ainda não tem documentos"}
          </p>
          <p className="font-normal text-[14px] sm:text-[16px] leading-[24px] text-[#60646c] opacity-90">
            Clique em &quot;Adicionar documentos&quot; ou arraste um documento, imagem ou outro arquivo para esta área.
          </p>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import closeXIcon from "../../assets/icons/close-x.svg";

interface DeleteConfirmModalProps {
  selectedCount: number;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export default function DeleteConfirmModal({
  selectedCount,
  onClose,
  onConfirm,
}: DeleteConfirmModalProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && !isDeleting) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDeleting, onClose]);

  const handleConfirm = async () => {
    setIsDeleting(true);
    try {
      await onConfirm();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4"
      onClick={() => {
        if (!isDeleting) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
        onClick={(e) => e.stopPropagation()}
        className="bg-[#fcfcfd] border border-[#d9d9e0] rounded-[12px] shadow-[0px_4px_8px_0px_rgba(0,0,0,0.04)] w-full max-w-[420px] flex flex-col overflow-hidden"
      >
        <div className="flex gap-[16px] items-center pb-[12px] pl-[16px] pr-[4px] pt-[4px] w-full">
          <div className="flex items-center gap-2.5 flex-1 pt-[6px]">
            <div className="p-1.5 rounded-[8px] bg-[#e5484d]/10 text-[#e5484d]">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h2
              id="delete-dialog-title"
              className="font-medium text-[#1c2024] text-[18px] leading-[20px]"
            >
              Confirmar exclusão
            </h2>
          </div>
          <button
            type="button"
            disabled={isDeleting}
            onClick={onClose}
            aria-label="Fechar modal"
            className="flex items-center justify-center rounded-[12px] size-[32px] hover:bg-[#f0f0f3] transition-colors disabled:opacity-50"
          >
            <img alt="" className="size-[16px]" src={closeXIcon} />
          </button>
        </div>

        <div className="px-[16px] pb-[16px] space-y-4">
          <p className="text-sm text-[#60646c] leading-relaxed">
            {selectedCount === 1
              ? "Tem certeza que deseja excluir o documento selecionado? Ele será removido permanentemente do AWS S3 e do banco de dados."
              : `Tem certeza que deseja excluir os ${selectedCount} documentos selecionados? Eles serão removidos permanentemente do AWS S3 e do banco de dados.`}
          </p>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              disabled={isDeleting}
              onClick={onClose}
              className="bg-[#f0f0f3] hover:bg-[#e4e4e9] px-[16px] py-[6px] rounded-[8px] font-medium text-[#60646c] text-sm transition-colors disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={isDeleting}
              onClick={() => void handleConfirm()}
              className="bg-[#e5484d] hover:bg-[#d1393e] flex items-center gap-2 px-[16px] py-[6px] rounded-[8px] font-medium text-[#fcfcfd] text-sm transition-colors disabled:opacity-60"
            >
              {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{isDeleting ? "Excluindo..." : "Excluir"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

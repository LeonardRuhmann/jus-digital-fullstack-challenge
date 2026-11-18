import { useEffect, useRef, useState } from "react";
import { Eye } from "lucide-react";
import plusIcon from "../../assets/icons/plus.svg";
import trashIcon from "../../assets/icons/trash.svg";

interface ActionBarProps {
  totalCount: number;
  selectedCount: number;
  onAddClick: () => void;
  onViewSelectedAnalysis: () => void;
  onDeleteSelected: () => void;
}

export default function ActionBar({
  totalCount,
  selectedCount,
  onAddClick,
  onViewSelectedAnalysis,
  onDeleteSelected,
}: ActionBarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // Close dropdown automatically if selection is cleared
  useEffect(() => {
    if (selectedCount === 0) {
      setDropdownOpen(false);
    }
  }, [selectedCount]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownOpen]);

  const isEmpty = totalCount === 0;

  return (
    <div className="flex flex-wrap gap-3 min-h-[40px] items-center justify-between w-full relative">
      {/* Left side: Document Counter (only shown when populated, per Figma 80:764) */}
      {!isEmpty ? (
        <div className="font-medium text-[#1c2024] text-[18px] sm:text-[20px] leading-[24px] tracking-[0.15px]">
          {totalCount} {totalCount === 1 ? "Documento" : "Documentos"}
        </div>
      ) : (
        <div />
      )}

      {/* Right side: Selection Pill + Dropdown & Add Document Button */}
      <div className="flex flex-wrap items-center gap-[8px] ml-auto">
        {selectedCount > 0 && (
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setDropdownOpen((prev) => !prev)}
              className="bg-[#f0f0f3] hover:bg-[#e4e4e9] flex items-center justify-center px-[16px] sm:px-[24px] py-[8px] rounded-[12px] text-[#60646c] font-medium text-[14px] sm:text-[16px] leading-[24px] transition-colors"
            >
              {selectedCount === 1
                ? "1 documento selecionado"
                : `${selectedCount} documentos selecionados`}
            </button>

            {/* Dropdown Menu (Figma nodes 80:882 for 1 selected, 80:1456 for >1 selected) */}
            {dropdownOpen && (
              <div className="absolute right-0 sm:left-0 mt-[8px] w-[280px] bg-[#fcfcfd] border border-[#d9d9e0] rounded-[12px] p-[4px] shadow-[0px_4px_8px_0px_rgba(0,0,0,0.04)] flex flex-col gap-[4px] z-30">
                <button
                  type="button"
                  onClick={() => {
                    setDropdownOpen(false);
                    onDeleteSelected();
                  }}
                  className="flex gap-[12px] items-center p-[6px] rounded-[6px] w-full hover:bg-[#f0f0f3] transition-colors text-left"
                >
                  <img
                    alt=""
                    className="size-[24px] shrink-0"
                    src={trashIcon}
                  />
                  <span className="font-medium text-[#60646c] text-[16px] tracking-[0.5px]">
                    Excluir documentos
                  </span>
                </button>

                {/* Subtle UX Rule from Figma 80:1441: Only show 'Visualizar analise' when 1 doc is selected */}
                {selectedCount === 1 && (
                  <button
                    type="button"
                    onClick={() => {
                      setDropdownOpen(false);
                      onViewSelectedAnalysis();
                    }}
                    className="flex gap-[12px] items-center p-[6px] rounded-[6px] w-full hover:bg-[#f0f0f3] transition-colors text-left"
                  >
                    <Eye className="size-[24px] text-[#60646c] shrink-0 stroke-[1.75]" />
                    <span className="font-medium text-[#60646c] text-[16px] tracking-[0.5px]">
                      Visualizar analise
                    </span>
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        <button
          type="button"
          onClick={onAddClick}
          className={
            isEmpty
              ? "bg-[#30a46c] hover:bg-[#29915e] flex gap-[8px] items-center justify-center pl-[12px] pr-[16px] py-[4px] rounded-[8px] transition-colors"
              : "bg-[#30a46c] hover:bg-[#29915e] flex gap-[8px] items-center justify-center pl-[16px] sm:pl-[20px] pr-[20px] sm:pr-[24px] py-[8px] rounded-[12px] transition-colors"
          }
        >
          <img
            alt=""
            className={isEmpty ? "size-[16px]" : "size-[20px] sm:size-[24px]"}
            src={plusIcon}
          />
          <span className="font-medium text-[15px] sm:text-[16px] leading-[24px] text-[#fcfcfd] whitespace-nowrap">
            Adicionar documento
          </span>
        </button>
      </div>
    </div>
  );
}

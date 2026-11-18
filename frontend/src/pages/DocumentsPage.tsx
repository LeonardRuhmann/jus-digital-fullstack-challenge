import Sidebar from "../components/layout/Sidebar";
import listMagnifyingGlassIcon from "../assets/icons/list-magnifying-glass.svg";
import plusIcon from "../assets/icons/plus.svg";

export default function DocumentsPage() {
  return (
    <div className="min-h-screen bg-[#fcfcfd] flex flex-col md:flex-row w-full">
      <Sidebar />

      {/* Main Content Area (Figma node 80:416) */}
      <main className="flex-1 flex flex-col gap-[24px] p-[16px] sm:p-[24px] min-w-0">
        <div className="flex flex-col items-start w-full">
          <h1 className="font-semibold text-[28px] sm:text-[32px] leading-[40px] text-[#1c2024]">
            Documentos
          </h1>
        </div>

        {/* White Container Card (Figma node 80:419) */}
        <div className="bg-white border border-[#d9d9e0] rounded-[12px] shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] flex-1 flex flex-col gap-[16px] pt-[16px] pb-[24px] px-[16px] sm:px-[24px] min-h-[520px]">
          {/* Action bar (Figma node 80:420) */}
          <div className="flex h-[40px] items-center justify-end w-full">
            <button
              type="button"
              className="bg-[#30a46c] hover:bg-[#29915e] flex gap-[8px] items-center justify-center pl-[12px] pr-[16px] py-[4px] h-[32px] rounded-[8px] transition-colors"
            >
              <img alt="" className="size-[16px]" src={plusIcon} />
              <span className="font-medium text-[16px] leading-[24px] text-[#fcfcfd] whitespace-nowrap">
                Adicionar documento
              </span>
            </button>
          </div>

          {/* Empty State Dashed Dropzone (Figma node 80:422) */}
          <div className="border border-[#d9d9e0] border-dashed rounded-[12px] flex-1 flex flex-col items-center justify-center p-6 text-center">
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
                  Você ainda não tem documentos
                </p>
                <p className="font-normal text-[14px] sm:text-[16px] leading-[24px] text-[#60646c] opacity-90">
                  Clique em &quot;Adicionar documentos&quot; para enviar um documento, imagem ou outro arquivo.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

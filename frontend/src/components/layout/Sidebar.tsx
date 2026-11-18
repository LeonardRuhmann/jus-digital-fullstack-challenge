import { useState } from "react";
import { LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import sidebarDocIcon from "../../assets/icons/sidebar-doc.svg";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [avatarError, setAvatarError] = useState(false);

  const initials = (user?.name || "U")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  const sidebarContent = (
    <aside
      className="bg-[#30a46c] flex flex-col justify-between h-full w-[255px] shrink-0 select-none"
      aria-label="Navegação lateral"
    >
      {/* Top Section: Office Header + Navigation Menu (Figma node 80:386) */}
      <div className="flex flex-col items-start w-full">
        <div className="flex flex-col items-start pt-[24px] pb-[8px] px-[8px] w-full">
          <div className="flex items-center justify-between gap-[8px] px-[8px] py-[8px] w-full">
            <div className="flex flex-col items-start min-w-0 flex-1">
              <p className="font-semibold text-[14px] leading-[20px] text-[#fbfefc] w-full truncate">
                Escritório
              </p>
              <p className="font-normal text-[12px] leading-[16px] text-[#c4e8d1] w-full truncate">
                Advogados associados
              </p>
            </div>
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="md:hidden p-1 rounded-[6px] text-[#fbfefc] hover:bg-[#5bb98b]/60 transition-colors"
              aria-label="Fechar menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <nav className="flex flex-col items-start px-[16px] py-[8px] w-full">
          <div className="flex flex-col gap-[4px] items-start w-full">
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="bg-[#5bb98b] flex gap-[8px] h-[32px] items-center p-[8px] rounded-[6px] w-full text-left transition-colors"
            >
              <div className="relative shrink-0 size-[16px]">
                <img
                  alt=""
                  className="block size-full"
                  src={sidebarDocIcon}
                />
              </div>
              <span className="font-normal text-[14px] leading-[20px] text-[#fbfefc] whitespace-nowrap">
                Documentos
              </span>
            </button>
          </div>
        </nav>
      </div>

      {/* Bottom Footer: Google OAuth User Profile (Figma node 80:409) */}
      <div className="flex flex-col items-start px-[8px] py-[24px] w-full">
        <div className="group flex gap-[8px] items-center p-[8px] rounded-[12px] w-full hover:bg-[#5bb98b]/40 transition-colors">
          <div className="relative rounded-[8px] shrink-0 size-[32px] overflow-hidden bg-[#5bb98b] flex items-center justify-center">
            {user?.avatar_url && !avatarError ? (
              <img
                src={user.avatar_url}
                alt={user.name}
                referrerPolicy="no-referrer"
                onError={() => setAvatarError(true)}
                className="size-full object-cover rounded-[8px]"
              />
            ) : (
              <span className="text-[12px] font-semibold text-[#fbfefc]">
                {initials}
              </span>
            )}
          </div>

          <div className="flex flex-col items-start min-w-0 flex-1 text-[#fbfefc]">
            <p
              className="font-semibold text-[14px] leading-[20px] w-full truncate"
              title={user?.name}
            >
              {user?.name || "Usuário"}
            </p>
            <p
              className="font-normal text-[12px] leading-[16px] w-full truncate"
              title={user?.email}
            >
              {user?.email || ""}
            </p>
          </div>

          <button
            type="button"
            onClick={() => void logout()}
            title="Sair da conta"
            aria-label="Sair da conta"
            className="opacity-70 hover:opacity-100 p-1.5 rounded-[6px] text-[#fbfefc] hover:bg-[#30a46c]/60 transition-all shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Mobile Top Header Bar (< 768px) */}
      <header className="md:hidden bg-[#30a46c] text-[#fbfefc] px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="p-1.5 rounded-[6px] hover:bg-[#5bb98b]/60 transition-colors"
            aria-label="Abrir menu lateral"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div>
            <p className="font-semibold text-[14px] leading-[18px]">Escritório</p>
            <p className="font-normal text-[11px] leading-[14px] text-[#c4e8d1]">
              Advogados associados
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="rounded-[8px] size-[28px] overflow-hidden bg-[#5bb98b] flex items-center justify-center">
            {user?.avatar_url && !avatarError ? (
              <img
                src={user.avatar_url}
                alt={user.name}
                referrerPolicy="no-referrer"
                onError={() => setAvatarError(true)}
                className="size-full object-cover"
              />
            ) : (
              <span className="text-[11px] font-semibold text-[#fbfefc]">
                {initials}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/40 transition-opacity"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative z-10 h-full">{sidebarContent}</div>
        </div>
      )}

      {/* Desktop Fixed Sidebar (>= 768px) */}
      <div className="hidden md:block h-screen sticky top-0 shrink-0">
        {sidebarContent}
      </div>
    </>
  );
}

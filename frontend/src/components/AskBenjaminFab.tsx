import { useState } from 'react';
import AskBenjaminPanel from './AskBenjaminPanel';

// Só visível abaixo do breakpoint lg — no desktop o chat vive sempre visível no painel
// lateral fixo (ver Layout.tsx). Aqui é um botão flutuante que abre o mesmo chat (mesmo
// AnalystChatContext, mesma conversa) num modal fullscreen.
export default function AskBenjaminFab() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Perguntar ao Benjamin"
        className="lg:hidden fixed bottom-20 right-4 z-40 w-14 h-14 rounded-full bg-navy-600 dark:bg-navy-500 text-white shadow-lg flex items-center justify-center text-2xl"
      >
        💬
      </button>

      {open && (
        <div
          className="lg:hidden fixed inset-0 z-50 bg-black/40 flex flex-col justify-end"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-gray-50 dark:bg-slate-950 rounded-t-2xl p-4 pb-6 max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <AskBenjaminPanel onClose={() => setOpen(false)} />
          </div>
        </div>
      )}
    </>
  );
}

import { Outlet } from 'react-router-dom';
import AskBenjaminFab from './AskBenjaminFab';
import AskBenjaminPanel from './AskBenjaminPanel';
import NavBar from './NavBar';
import SideNav from './SideNav';

// Mobile: navegação em baixo (NavBar). Desktop (lg:): navegação lateral fixa à
// esquerda (SideNav) + duas colunas no conteúdo — página + painel fixo "Perguntar ao
// Benjamin" à direita (sticky, sempre visível, em todas as páginas). Abaixo de lg não há
// espaço para nenhuma das duas colunas, por isso o chat vira um botão flutuante
// (AskBenjaminFab) e a navegação volta para a barra de baixo.
export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 lg:flex">
      <SideNav />
      <div className="flex-1 pb-16 lg:pb-0 min-w-0">
        <main className="max-w-md md:max-w-2xl lg:max-w-5xl mx-auto px-4 pt-4 lg:px-8 lg:py-6 lg:grid lg:grid-cols-[1fr_360px] lg:gap-6 lg:items-start">
          <div className="min-w-0">
            <Outlet />
          </div>
          <aside className="hidden lg:block lg:sticky lg:top-6">
            <AskBenjaminPanel />
          </aside>
        </main>
      </div>
      <AskBenjaminFab />
      <NavBar />
    </div>
  );
}

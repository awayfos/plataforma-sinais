import { Cabecalho } from "@/components/sessao/Cabecalho";
import { ProvedorSessao } from "@/components/sessao/ProvedorSessao";
import { AvisoRisco } from "@/components/ui/AvisoRisco";
import { ProvedorTempoReal } from "@/lib/ws/ProvedorTempoReal";

export default function LayoutApp({ children }: { children: React.ReactNode }) {
  return (
    <ProvedorSessao>
      <ProvedorTempoReal>
        <div className="flex min-h-dvh flex-col">
          <a href="#conteudo" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded focus:bg-ouro focus:px-3 focus:py-1 focus:text-fundo">
            Pular para o conteúdo
          </a>
          <Cabecalho />
          <div id="conteudo" className="flex min-h-0 flex-1 flex-col">
            {children}
          </div>
          <div className="sticky bottom-0 z-30">
            <AvisoRisco />
          </div>
        </div>
      </ProvedorTempoReal>
    </ProvedorSessao>
  );
}

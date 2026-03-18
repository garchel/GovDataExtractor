# GovDataExtractor🤖 GovDataExtractor - RPA & Hiperautomação
Este projeto consiste em um robô autônomo desenvolvido em Python e Playwright para extração de dados e evidências do Portal da Transparência. O foco principal foi a resiliência contra instabilidades do portal e a precisão na sincronização de dados assíncronos.

🛠️ Decisões Técnicas
1. Escolha da Stack: Playwright (Async)
A escolha do Playwright em modo assíncrono (asyncio) foi motivada pela necessidade de:

Execução Simultânea: Permitir que múltiplos bots rodem ao mesmo tempo sem bloquear a CPU.

Auto-wait nativo: Diferente do Selenium, o Playwright aguarda que os elementos estejam "actionable" (visíveis e estáveis) antes de interagir.
---
2. Arquitetura do Scraper
O robô foi estruturado em uma classe PortalScraper, separando a lógica de navegação da lógica de extração. Isso facilita a manutenção caso o Governo Federal altere seletores CSS específicos.

🚀 Desafios Enfrentados e Soluções
🧩 Desafio 1: Sincronização e Race Conditions (Cenário 5)
Durante os testes de busca por sobrenome ("Oliveira"), o robô coletava dados do teste anterior antes que a página atualizasse. O portal utiliza AJAX para atualizar os resultados sem recarregar a URL.

Solução: Implementação de uma Sincronização Híbrida. O robô agora invalida o resultado anterior e aguarda uma mudança real no texto do contador de resultados (#countResultados) ou no link do primeiro registro, garantindo que o dado extraído pertença à busca atual.

🧩 Desafio 2: Interação com Filtros Sociais (Shadow DOM/Overlays)
O checkbox de "Beneficiário de Programa Social" não permitia o clique direto por estar sobreposto por elementos de estilo (CSS customizado do portal).

Solução: Uso do parâmetro force=True no método click() e interação direta com o label associado ao ID do checkbox. Isso garante a marcação do filtro mesmo que o elemento original esteja com opacity: 0 ou escondido atrás de um ícone.

🧩 Desafio 3: Navegação em Acordeões e Histórico
Ao clicar em "Detalhar" um benefício, o robô navega para uma nova página. Ao retornar (page.go_back()), o acordeão de recursos frequentemente voltava ao estado fechado.

Solução: Implementação de uma verificação de estado do atributo aria-expanded. Caso o acordeão feche após a volta, o robô o reabre automaticamente para prosseguir com a coleta do próximo benefício da lista.
---
📊 Estrutura de Saída (JSON)
O robô gera um objeto estruturado seguindo o padrão exigido:
````
{
  "status": "success",
  "identificador": "73665657172",
  "panorama": {
    "nome": "PAULO VICTOR...",
    "cpf": "***.656.571-**",
    "localidade": "BRASÍLIA - DF"
  },
  "evidencia_principal": "iVBORw0KGgoAAAANSUh...",
  "beneficios": [
    {
      "tipo": "Auxílio Emergencial",
      "valor_total": "R$ 3.000,00",
      "evidencia_base64": "iVBORw0KGgoAAAANSUh..."
    }
  ]
}
````

⚡ Como Executar
Instale as dependências: pip install playwright pytest

Instale os navegadores: playwright install chromium

Execute os testes: python main_test.py
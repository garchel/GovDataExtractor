# 🤖 GovDataExtractor - RPA & Hiperautomação
Este projeto consiste em um microsserviço de automação robótica (RPA) desenvolvido em Python e Playwright para a extração assistida de dados e evidências do Portal da Transparência.

O diferencial desta solução é sua arquitetura modular e a disponibilização via API REST (FastAPI).

## Arquitetura e Modularização

***config.py:*** Centraliza seletores CSS, URLs e timeouts. Facilita a manutenção rápida caso o layout do portal mude.

***browser.py:*** Gerencia o ciclo de vida do navegador com integração de Stealth Mode para evitar detecção por WAF/Bot-Blockers.

***utils.py:*** Funções puras de processamento (Regex de CPF, conversão Base64 e slugificação de nomes).

***scraper.py:*** A lógica core do RPA, focada puramente na navegação e extração.

***api.py:*** Interface FastAPI que expõe o robô como um serviço documentado via Swagger.

## Como Executar
Você pode rodar o projeto localmente ou via Docker.

**Opção 1:** Via Docker (Recomendado)
Certifique-se de ter o Docker instalado e execute:

````Bash
docker-compose up --build
````
A API estará disponível em http://localhost:8000.

**Opção 2:** Localmente

1. Crie e ative o ambiente virtual:

````Bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
````

2. Instale as dependências:

````Bash
pip install -r requirements.txt
````
3. Instale os binários do Playwright:

````Bash
playwright install firefox
````

4. Inicie a API:

````Bash
python api.py
````

## Documentação da API (Swagger)
Uma vez que a aplicação esteja rodando, acesse a documentação interativa oficial:
 http://localhost:8000/docs

Nesta página, você poderá testar os endpoints diretamente, visualizando os esquemas de entrada e saída (JSON) em tempo real.

## Desafios Enfrentados e Soluções Técnicas
1. Sincronização AJAX (Race Conditions)
O portal atualiza resultados via chamadas assíncronas sem recarregar a URL.

Solução: Implementação de uma sincronização híbrida no método _validar_e_selecionar_resultado, que valida a mudança no texto do contador (#countResultados) antes de prosseguir, evitando que o bot colete dados do teste anterior.

2. Evasão de Detecção (Bot Detection)
Sites governamentais possuem camadas de segurança contra automações simples.

Solução: Implementação da biblioteca playwright-stealth e sobreescrita da propriedade navigator.webdriver. Além disso, o uso do navegador Firefox (via Playwright) em modo headless demonstrou maior estabilidade contra desafios de rede.

3. Extração Multinível de Benefícios
Coletar dados de acordeões dinâmicos (Auxílio Brasil, Bolsa Família) exige gerenciar o estado do DOM.

Solução: O robô itera sobre as tabelas de recursos, clica em "Detalhar", captura a evidência em Base64 e utiliza page.go_back() com espera por networkidle, garantindo que o contexto seja preservado para o próximo benefício da lista.

## Estrutura de Saída (JSON)
Exemplo de resposta de sucesso:

````JSON
{
  "status": "success",
  "identificador": "73665649153",
  "panorama": {
    "nome": "MARIA BARBARA...",
    "cpf": "***.656.491-**",
    "localidade": "BRASÍLIA - DF"
  },
  "evidencia_principal": "iVBORw0KGgoAAAANSUhEUgAA...",
  "beneficios": [
    {
      "tipo": "Auxílio Emergencial",
      "valor_total": "R$ 4.200,00",
      "evidencia_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
    }
  ]
}
````

## Tecnologias Utilizadas
Python 3.10+

Playwright (Automação Web)

FastAPI (Interface de API & Swagger)

Uvicorn (Servidor ASGI)

Docker & Docker Compose (Containerização)

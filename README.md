# 🤖 GovDataExtractor - RPA & Hiperautomação
Este projeto consiste em um ecossistema de hiperautomação que combina um microsserviço de RPA (Python + Playwright) com um workflow de orquestração (n8n) para extração, armazenamento e registro de dados do Portal da Transparência.

## Arquitetura da Solução

O projeto é dividido em duas camadas principais:

1. **Worker API (RPA)**: Container Python/FastAPI que executa o robô Playwright.

2. **Orquestrador (n8n)**: Workflow que gerencia o ciclo de vida da consulta:

````Requisição API → Processamento → Geração de JSON → Upload Google Drive → Log Google Sheets.````

## Organização dos Arquivos

- **config.py:** Centraliza seletores CSS, URLs e timeouts. Facilita a manutenção rápida caso o layout do portal mude.

- **browser.py:** Gerencia o ciclo de vida do navegador com integração de Stealth Mode para evitar detecção por WAF/Bot-Blockers.

- **utils.py:** Funções puras de processamento (Regex de CPF, conversão Base64 e slugificação de nomes).

- **scraper.py:** A lógica core do RPA, focada puramente na navegação e extração.

- **api.py:** Interface FastAPI que expõe o robô como um serviço documentado via Swagger.

## Diferenciais Técnicos
- **Modularização**: Código separado por responsabilidades (Browser, Scraper, API, Utils).

- **Stealth Mode**: Integração de técnicas para evitar detecção por WAF/Bot-Blockers.

- **Escalabilidade**: Orquestração preparada para execuções sequenciais (Batching), garantindo integridade dos dados.

## Como Executar (Docker)
Esta é a forma recomendada, pois configura automaticamente a API e o ambiente do n8n.

1. Certifique-se de ter o Docker e Docker Compose instalados e **abertos**.

2. Na raiz do projeto, execute:

````Bash
docker-compose up --build -d
````
3. **Acessos**:

- **API (Swagger)**: http://localhost:8000/docs

- **n8n**: http://localhost:5678

## Configuração do Workflow (n8n)
Para testar a Parte 2 (Hiperautomação), siga os passos:

1. Acesse o n8n em http://localhost:5678.

2. Crie um novo workflow e importe o arquivo workflow_n8n_most.json (Botão de 3 pontos no canto superior direito > Import from File).

3. 🚨 Credenciais: Por questões de segurança e boas práticas de desenvolvimento (LGPD/OWASP), as credenciais OAuth 2.0 não foram incluídas no repositório.  
- **Nota Técnica**: Para validar a integração com Drive/Sheets, o avaliador deverá configurar seu próprio Client ID e Secret no console do Google Cloud e vinculá-los ao n8n.
- **Demonstração**: Caso prefira não configurar as chaves, a Parte 1 (RPA) pode ser testada via Swagger e a Parte 2 (Hiperautomação) será demonstrada em pleno funcionamento durante a apresentação técnica agendada.

4. O workflow já está configurado com os **5 cenários de teste solicitados no desafio** (Sucesso CPF, Erro CPF, Sucesso Nome, Erro Nome e Filtro Social).

## Desafios Enfrentados e Soluções Técnicas
1. **Sincronização AJAX (Race Conditions)** O portal atualiza resultados via chamadas assíncronas sem recarregar a URL.  
**Solução**: Implementação de uma sincronização híbrida no método _validar_e_selecionar_resultado, que valida a mudança no texto do contador (#countResultados) antes de prosseguir, evitando que o bot colete dados do teste anterior.

2. **Evasão de Detecção (Bot Detection)** Sites governamentais possuem camadas de segurança contra automações simples.  
**Solução**: Implementação da biblioteca playwright-stealth e sobreescrita da propriedade navigator.webdriver. Além disso, o uso do navegador Firefox (via Playwright) em modo headless demonstrou maior estabilidade contra desafios de rede.

3. **Extração Multinível de Benefícios** Coletar dados de acordeões dinâmicos (Auxílio Brasil, Bolsa Família) exige gerenciar o estado do DOM.  
**Solução**: O robô itera sobre as tabelas de recursos, clica em "Detalhar", captura a evidência em Base64 e utiliza page.go_back() com espera por networkidle, garantindo que o contexto seja preservado para o próximo benefício da lista.

4. **Orquestração em Lote (Batching)** Disparar 5 consultas simultâneas causava concorrência no contexto do navegador (Playwright).  
**Solução**: No n8n, utilizamos o nó Loop Over Items com processamento sequencial. Isso garante que cada consulta tenha uma instância limpa e estável do navegador no Docker.

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

## Cenários de Teste Cobertos
O nó Code no n8n executa automaticamente:

- **Sucesso (CPF)**: Retorno de dados estruturados e evidência.

- **Erro (CPF)**: Mensagem "Não foi possível retornar os dados...".

- **Sucesso (Nome)**: Coleta do primeiro registro encontrado.

- **Erro (Nome)**: Mensagem "Foram encontrados 0 resultados...".

- **Filtrado**: Busca por sobrenome com aplicação de filtro de programa social.

## Tecnologias Utilizadas
- **Python 3.10+**

- **Playwright** (Automação Web)

- **FastAPI** (Interface de API & Swagger)

- **Uvicorn** (Servidor ASGI)

- **n8n** (Hiperautomação e Integrações Google)

- **Docker & Docker Compose** (Containerização)

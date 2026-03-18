import base64
import asyncio
import re
import os
from playwright.async_api import async_playwright, expect, Page
from playwright_stealth import Stealth

class PortalScraper:
    def __init__(self):
        self.url_busca = "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"
        self.base_dir = "evidencias_portal"

    # --- 1. CONFIGURAÇÃO DO BROWSER (SETUP) ---

    async def _configurar_navegador(self, playwright):
        """Configura browser, contexto com stealth e nova página."""
        browser = await playwright.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            viewport={'width': 1280, 'height': 720},
        )
        stealth = Stealth()
        await stealth.apply_stealth_async(context)
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return browser, page

    # --- 2. MECANISMO DE BUSCA ---

    async def _executar_busca(self, page: Page, identificador: str, filtro_social: bool):
        """Preenche os campos e aplica filtros de busca."""
        print(f"[*] Iniciando busca para: {identificador}")
        await page.goto(self.url_busca, wait_until="networkidle", timeout=60000)
        
        await page.fill("#termo", "")
        if filtro_social:
            print("[*] Aplicando filtro de programa social...")
            await page.click('button[aria-controls="box-busca-refinada"]')
            label_social = page.locator("label[for='beneficiarioProgramaSocial']")
            await label_social.wait_for(state="visible")
            await label_social.click(force=True)
        
        await page.fill("#termo", identificador)
        await page.keyboard.press("Enter")

    # --- 3. SELEÇÃO DE RESULTADOS (HANDSHAKE) ---

    async def _validar_e_selecionar_resultado(self, page: Page, identificador: str):
        """Valida se o resultado apareceu e se corresponde ao termo buscado."""
        print("[*] Aguardando atualização dos resultados...")
        tokens_busca = [t.upper() for t in identificador.split() if len(t) > 2] if not self._e_identificador_numerico(identificador) else []

        for _ in range(30):
            await page.wait_for_load_state("networkidle")
            primeiro_link = page.locator(".link-busca-nome").first
            if await primeiro_link.count() > 0:
                if self._e_identificador_numerico(identificador): break
                nome_na_tela = (await primeiro_link.inner_text()).upper()
                if all(token in nome_na_tela for token in tokens_busca): break
            await page.wait_for_timeout(500)

        texto_resultados = (await page.locator("#countResultados").inner_text()).strip()
        if "0 resultados" in texto_resultados or texto_resultados == "0":
            return False

        link_resultado = page.locator(".link-busca-nome").first
        await link_resultado.wait_for(state="visible", timeout=10000)
        await link_resultado.click()
        return True

    # --- MÉTODOS UTILITÁRIOS E DE EXTRAÇÃO (MANTIDOS) ---

    def _e_identificador_numerico(self, texto: str) -> bool:
        return len(re.sub(r'\D', '', texto)) == 11

    def _gerar_caminho_evidencia(self, nome: str, cpf: str) -> str:
        nome_slug = re.sub(r'[^\w\s-]', '', nome).strip().replace(' ', '_')
        cpf_limpo = re.sub(r'\D', '', cpf)
        caminho = os.path.join(self.base_dir, f"{nome_slug}_{cpf_limpo}")
        if not os.path.exists(caminho): os.makedirs(caminho)
        return caminho

    def _converter_para_base64(self, caminho_arquivo: str) -> str:
        with open(caminho_arquivo, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

    async def _limpar_tela_para_evidencia(self, page: Page):
        await page.evaluate("""
            const seletores = ['#card0', '.br-modal-scrim', '.aws-waf-captcha-container', '#cookiebar-container-fluid'];
            seletores.forEach(sel => {
                const el = document.querySelector(sel);
                if (el) el.remove();
            });
            document.body.style.overflow = 'auto';
        """)

    async def _extrair_panorama(self, page: Page):
        return {
            "nome": (await page.locator("strong:has-text('Nome') + span").inner_text()).strip(),
            "cpf": (await page.locator("strong:has-text('CPF') + span").inner_text()).strip(),
            "localidade": (await page.locator("strong:has-text('Localidade') + span").inner_text()).strip()
        }

    async def _extrair_beneficios(self, page: Page, caminho_pessoa: str):
        beneficios_coletados = []
        btn_recursos = page.locator("button[aria-controls='accordion-recebimentos-recursos']")
        tabelas = page.locator("#accordion-recebimentos-recursos .responsive")
        total_tabelas = await tabelas.count()
        
        for i in range(total_tabelas):
            tabela = tabelas.nth(i)
            nome_beneficio = await tabela.locator("strong").first.inner_text()
            if any(x in nome_beneficio for x in ["Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família"]):
                linha = tabela.locator("tbody tr").first
                valor = await linha.locator("td").nth(3).inner_text()
                await linha.locator("text=Detalhar").click()
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(2000) 
                await self._limpar_tela_para_evidencia(page)
                nome_ben_slug = re.sub(r'[^\w\s-]', '', nome_beneficio).strip().replace(' ', '_')
                foto_beneficio = os.path.join(caminho_pessoa, f"beneficio_{i}_{nome_ben_slug}.png")
                await page.screenshot(path=foto_beneficio, full_page=True)
                beneficios_coletados.append({
                    "tipo": nome_beneficio.strip(),
                    "valor_total": valor.strip(),
                    "evidencia_base64": self._converter_para_base64(foto_beneficio)
                })
                await page.go_back(wait_until="networkidle")
                if i < total_tabelas - 1:
                    await btn_recursos.click()
                    await page.wait_for_timeout(1000)
        return beneficios_coletados

    # --- ORQUESTRADOR ---

    async def consultar(self, identificador: str, filtro_social: bool = False):
        async with async_playwright() as p:
            browser, page = await self._configurar_navegador(p)

            try:
                # Executa busca
                await self._executar_busca(page, identificador, filtro_social)

                # Handshake e Seleção
                sucesso_selecao = await self._validar_e_selecionar_resultado(page, identificador)
                if not sucesso_selecao:
                    msg = "Não foi possível retornar os dados no tempo de resposta solicitado." if self._e_identificador_numerico(identificador) else f"Foram encontrados 0 resultados para o termo {identificador}."
                    return {"status": "error", "mensagem": msg}

                # Preparação da página interna
                await page.wait_for_selector("strong:has-text('Nome')", timeout=20000)
                await page.wait_for_load_state("networkidle")

                print("[*] Abrindo seção de Recursos...")
                btn_recursos = page.locator("button[aria-controls='accordion-recebimentos-recursos']")
                try:
                    await btn_recursos.wait_for(state="visible", timeout=5000)
                    await btn_recursos.click()
                    await page.wait_for_timeout(1500)
                except:
                    print(f"[!] Aviso: Botão de recursos não encontrado.")

                # Extração e Evidências
                panorama_dados = await self._extrair_panorama(page)
                caminho_pessoa = self._gerar_caminho_evidencia(panorama_dados['nome'], panorama_dados['cpf'])

                await self._limpar_tela_para_evidencia(page)
                foto_panorama = os.path.join(caminho_pessoa, "00_panorama_geral.png")
                await page.screenshot(path=foto_panorama, full_page=True)
                main_evidence = self._converter_para_base64(foto_panorama)

                beneficios = await self._extrair_beneficios(page, caminho_pessoa)

                print("[+] Automação finalizada com sucesso.")
                return {
                    "status": "success",
                    "identificador": identificador,
                    "panorama": panorama_dados,
                    "evidencia_principal": main_evidence,
                    "beneficios": beneficios
                }

            except Exception as e:
                print(f"[ERROR] Erro na captura: {str(e)}")
                return {"status": "error", "mensagem": "Erro interno no processamento dos dados."}
            finally:
                await browser.close()
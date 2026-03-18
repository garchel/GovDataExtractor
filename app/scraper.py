import os
import asyncio
from playwright.async_api import async_playwright, Page
from config import Config
from utils import Utils
from browser import BrowserFactory

class PortalScraper:
    def __init__(self):
        self.config = Config()
        self.utils = Utils()

    async def _limpar_tela_para_evidencia(self, page: Page):
        await page.evaluate("""
            const seletores = ['#card0', '.br-modal-scrim', '.aws-waf-captcha-container', '#cookiebar-container-fluid'];
            seletores.forEach(sel => {
                const el = document.querySelector(sel);
                if (el) el.remove();
            });
            document.body.style.overflow = 'auto';
        """)

    async def _executar_busca(self, page: Page, identificador: str, filtro_social: bool):
        print(f"[*] Iniciando busca para: {identificador}")
        await page.goto(self.config.URL_BUSCA, wait_until="networkidle", timeout=self.config.TIMEOUT_PADRAO)
        
        await page.fill(self.config.INPUT_BUSCA, "")
        if filtro_social:
            print("[*] Aplicando filtro de programa social...")
            await page.click(self.config.BTN_FILTRO_REFINADO)
            label_social = page.locator(self.config.LABEL_SOCIAL)
            await label_social.wait_for(state="visible")
            await label_social.click(force=True)
        
        await page.fill(self.config.INPUT_BUSCA, identificador)
        await page.keyboard.press("Enter")

    async def _validar_e_selecionar_resultado(self, page: Page, identificador: str):
        print("[*] Aguardando atualização dos resultados...")
        is_num = self.utils.e_identificador_numerico(identificador)
        tokens_busca = [t.upper() for t in identificador.split() if len(t) > 2] if not is_num else []

        for _ in range(30):
            await page.wait_for_load_state("networkidle")
            primeiro_link = page.locator(self.config.LINK_RESULTADO_NOME).first
            if await primeiro_link.count() > 0:
                if is_num: break
                nome_na_tela = (await primeiro_link.inner_text()).upper()
                if all(token in nome_na_tela for token in tokens_busca): break
            await page.wait_for_timeout(500)

        texto_resultados = (await page.locator(self.config.COUNT_RESULTADOS).inner_text()).strip()
        if "0 resultados" in texto_resultados or texto_resultados == "0":
            return False

        link_resultado = page.locator(self.config.LINK_RESULTADO_NOME).first
        await link_resultado.wait_for(state="visible", timeout=10000)
        await link_resultado.click()
        return True

    async def _extrair_panorama(self, page: Page):
        return {
            "nome": (await page.locator(self.config.LABEL_NOME).inner_text()).strip(),
            "cpf": (await page.locator(self.config.LABEL_CPF).inner_text()).strip(),
            "localidade": (await page.locator(self.config.LABEL_LOCALIDADE).inner_text()).strip()
        }

    async def _extrair_beneficios(self, page: Page, caminho_pessoa: str):
        beneficios_coletados = []
        btn_recursos = page.locator(self.config.BTN_RECURSOS)
        tabelas = page.locator(self.config.TABELAS_RECURSOS)
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
                
                nome_ben_slug = self.utils.slugify(nome_beneficio)
                foto_beneficio = os.path.join(caminho_pessoa, f"beneficio_{i}_{nome_ben_slug}.png")
                await page.screenshot(path=foto_beneficio, full_page=True)
                
                beneficios_coletados.append({
                    "tipo": nome_beneficio.strip(),
                    "valor_total": valor.strip(),
                    "evidencia_base64": self.utils.converter_para_base64(foto_beneficio)
                })
                await page.go_back(wait_until="networkidle")
                if i < total_tabelas - 1:
                    await btn_recursos.click()
                    await page.wait_for_timeout(1000)
        return beneficios_coletados

    async def consultar(self, identificador: str, filtro_social: bool = False):
        async with async_playwright() as p:
            browser, page = await BrowserFactory.configurar_navegador(p)
            try:
                await self._executar_busca(page, identificador, filtro_social)
                
                sucesso_selecao = await self._validar_e_selecionar_resultado(page, identificador)
                if not sucesso_selecao:
                    msg = "Não foi possível retornar os dados no tempo de resposta solicitado." if self.utils.e_identificador_numerico(identificador) else f"Foram encontrados 0 resultados para o termo {identificador}."
                    return {"status": "error", "mensagem": msg}

                await page.wait_for_selector(self.config.LABEL_NOME, timeout=20000)
                await page.wait_for_load_state("networkidle")

                print("[*] Abrindo seção de Recursos...")
                btn_recursos = page.locator(self.config.BTN_RECURSOS)
                try:
                    await btn_recursos.wait_for(state="visible", timeout=5000)
                    await btn_recursos.click()
                    await page.wait_for_timeout(1500)
                except:
                    print(f"[!] Aviso: Botão de recursos não encontrado.")

                panorama_dados = await self._extrair_panorama(page)
                caminho_pessoa = self.utils.gerar_caminho_evidencia(self.config.BASE_DIR, panorama_dados['nome'], panorama_dados['cpf'])

                await self._limpar_tela_para_evidencia(page)
                foto_panorama = os.path.join(caminho_pessoa, "00_panorama_geral.png")
                await page.screenshot(path=foto_panorama, full_page=True)
                
                main_evidence = self.utils.converter_para_base64(foto_panorama)
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
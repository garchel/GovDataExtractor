import base64
import asyncio
import re
import os
from playwright.async_api import async_playwright, expect
from playwright_stealth import Stealth

class PortalScraper:
    def __init__(self):
        self.url_busca = "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"
        self.base_dir = "evidencias_portal"

    def e_identificador_numerico(self, texto: str) -> bool:
        apenas_numeros = re.sub(r'\D', '', texto)
        return len(apenas_numeros) == 11

    async def limpar_tela_para_evidencia(self, page):
        """
        Remove elementos obstrutivos (Cookies, WAF, Modais) via JavaScript 
        para garantir que a evidência saia limpa.
        """
        print("[*] Limpando elementos obstrutivos da tela via DOM...")
        await page.evaluate("""
            const seletores = [
                '#card0',                      // Banner de Cookies
                '.br-modal-scrim',             // Fundo escuro do modal
                '.aws-waf-captcha-container',  // Container do WAF
                '#cookiebar-container-fluid'   // Container alternativo de cookies
            ];
            seletores.forEach(sel => {
                const el = document.querySelector(sel);
                if (el) el.remove();
            });
            // Remove o 'lock' de scroll que alguns modais impõem ao corpo da página
            document.body.style.overflow = 'auto';
        """)

    async def consultar(self, identificador: str, filtro_social: bool = False):
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
                viewport={'width': 1280, 'height': 720},
            )

            stealth = Stealth()
            await stealth.apply_stealth_async(context)

            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            try:
                print(f"[*] Iniciando busca para: {identificador}")
                await page.goto(self.url_busca, wait_until="networkidle", timeout=60000)

                # 1. Limpeza e Preenchimento
                await page.fill("#termo", "")

                if filtro_social:
                    print("[*] Aplicando filtro de programa social...")
                    await page.click('button[aria-controls="box-busca-refinada"]')
                    label_social = page.locator("label[for='beneficiarioProgramaSocial']")
                    await label_social.wait_for(state="visible")
                    await label_social.click(force=True)
                
                await page.fill("#termo", identificador)
                await page.keyboard.press("Enter")

                # 2. Sincronização
                print("[*] Aguardando atualização dos resultados...")
                tokens_busca = []
                if not self.e_identificador_numerico(identificador):
                    tokens_busca = [t.upper() for t in identificador.split() if len(t) > 2]

                for _ in range(30):
                    await page.wait_for_load_state("networkidle")
                    primeiro_link = page.locator(".link-busca-nome").first
                    if await primeiro_link.count() > 0:
                        if self.e_identificador_numerico(identificador):
                            break
                        nome_na_tela = (await primeiro_link.inner_text()).upper()
                        if all(token in nome_na_tela for token in tokens_busca):
                            break
                    await page.wait_for_timeout(500)

                # 3. Validação Final
                texto_resultados = (await page.locator("#countResultados").inner_text()).strip()
                if "0 resultados" in texto_resultados or texto_resultados == "0":
                    msg = "Não foi possível retornar os dados no tempo de resposta solicitado." if self.e_identificador_numerico(identificador) else f"Foram encontrados 0 resultados para o termo {identificador}."
                    return {"status": "error", "mensagem": msg}

                # 4. Acesso ao Registro
                print("[*] Clicando no primeiro resultado...")
                link_resultado = page.locator(".link-busca-nome").first
                await link_resultado.wait_for(state="visible", timeout=10000)
                await link_resultado.click()
                
                await page.wait_for_selector("strong:has-text('Nome')", timeout=20000)
                await page.wait_for_load_state("networkidle")

                # 5. Coleta Panorama e Salvamento de Evidência 1
                panorama_dados = {
                    "nome": (await page.locator("strong:has-text('Nome') + span").inner_text()).strip(),
                    "cpf": (await page.locator("strong:has-text('CPF') + span").inner_text()).strip(),
                    "localidade": (await page.locator("strong:has-text('Localidade') + span").inner_text()).strip()
                }

                nome_pasta = re.sub(r'[^\w\s-]', '', panorama_dados['nome']).strip().replace(' ', '_')
                cpf_pasta = re.sub(r'\D', '', panorama_dados['cpf'])
                caminho_pessoa = os.path.join(self.base_dir, f"{nome_pasta}_{cpf_pasta}")
                if not os.path.exists(caminho_pessoa): os.makedirs(caminho_pessoa)

                # --- LIMPEZA ANTES DO PRIMEIRO PRINT ---
                await self.limpar_tela_para_evidencia(page)
                foto_panorama = os.path.join(caminho_pessoa, "00_panorama_geral.png")
                

                # Referencia o botao Recebimento de Recursos
                beneficios_coletados = []
                btn_recursos = page.locator("button[aria-controls='accordion-recebimentos-recursos']")

                # Abre os recursos
                await btn_recursos.click()
                await page.wait_for_timeout(1500)

                # Printa o Panorama
                await page.screenshot(path=foto_panorama, full_page=True)
                with open(foto_panorama, "rb") as img_file:
                    main_evidence = base64.b64encode(img_file.read()).decode('utf-8')

                print("[*] Iniciando Coleta de Benefícios...")
                # 6. Coleta de Benefícios
                if await btn_recursos.count() > 0:
                    

                    tabelas = page.locator("#accordion-recebimentos-recursos .responsive")
                    total_tabelas = await tabelas.count()
                    
                    for i in range(total_tabelas):
                        tabela = tabelas.nth(i)
                        nome_beneficio = await tabela.locator("strong").first.inner_text()
                        
                        if any(x in nome_beneficio for x in ["Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família"]):
                            print(f"[*] Detalhando: {nome_beneficio.strip()}")
                            linha = tabela.locator("tbody tr").first
                            valor = await linha.locator("td").nth(3).inner_text()
                            
                            await linha.locator("text=Detalhar").click()
                            await page.wait_for_load_state("networkidle")
                            await page.wait_for_timeout(2000) # Tempo para o WAF/Modal carregar

                            # --- LIMPEZA ANTES DO PRINT DO BENEFÍCIO ---
                            # Aqui removemos o WAF se ele tiver aparecido no clique do detalhar
                            await self.limpar_tela_para_evidencia(page)

                            nome_ben_slug = re.sub(r'[^\w\s-]', '', nome_beneficio).strip().replace(' ', '_')
                            foto_beneficio = os.path.join(caminho_pessoa, f"beneficio_{i}_{nome_ben_slug}.png")
                            await page.screenshot(path=foto_beneficio, full_page=True)

                            with open(foto_beneficio, "rb") as img_file:
                                evidence_detail = base64.b64encode(img_file.read()).decode('utf-8')
                            
                            beneficios_coletados.append({
                                "tipo": nome_beneficio.strip(),
                                "valor_total": valor.strip(),
                                "evidencia_base64": evidence_detail
                            })
                            
                            await page.go_back(wait_until="networkidle")
                            if i < total_tabelas - 1:
                                await btn_recursos.click()
                                await page.wait_for_timeout(1000)

                print("[+] Automação finalizada com sucesso.")
                return {
                    "status": "success",
                    "identificador": identificador,
                    "panorama": panorama_dados,
                    "evidencia_principal": main_evidence,
                    "beneficios": beneficios_coletados
                }

            except Exception as e:
                print(f"[ERROR] Erro na captura: {str(e)}")
                return {"status": "error", "mensagem": "Erro interno no processamento dos dados."}
            finally:
                await browser.close()
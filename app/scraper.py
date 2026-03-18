import base64
import asyncio
import re
from playwright.async_api import async_playwright

class PortalScraper:
    def __init__(self):
        self.url_busca = "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"

    def e_identificador_numerico(self, texto: str) -> bool:
        # Remove caracteres de formatação para validar apenas os dígitos
        apenas_numeros = re.sub(r'\D', '', texto)
        # CPF e NIS possuem 11 dígitos
        return len(apenas_numeros) == 11

    async def consultar(self, identificador: str, filtro_social: bool = False):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"[*] Iniciando busca para: {identificador}")
                await page.goto(self.url_busca, wait_until="networkidle", timeout=60000)

                # Preenchimento do termo
                await page.fill("#termo", identificador)

                if filtro_social:
                    print("[*] Aplicando filtro de programa social...")
                    btn_refinar = page.locator('button[aria-controls="box-busca-refinada"]')
                    await btn_refinar.click()
                    
                    checkbox = page.locator("#beneficiarioProgramaSocial")
                    await checkbox.wait_for(state="visible")
                    await checkbox.check()
                    
                    await page.click("#btnConsultarPF")
                else:
                    await page.keyboard.press("Enter")

                # Espera a renderização dos resultados
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2500) 
                
                container_resultados = page.locator("#countResultados")
                texto_resultados = (await container_resultados.inner_text()).strip() if await container_resultados.count() > 0 else "0"

                # --- AJUSTE DE MENSAGENS DE ERRO ---
                if texto_resultados == "0":
                    if self.e_identificador_numerico(identificador):
                        # Caso seja CPF ou NIS inexistente
                        return {
                            "status": "error",
                            "mensagem": "Não foi possível retornar os dados no tempo de resposta solicitado."
                        }
                    else:
                        # Caso seja um Nome inexistente
                        return {
                            "status": "error", 
                            "mensagem": f"Foram encontrados 0 resultados para o termo {identificador}."
                        }

                # Entrar no Panorama
                print("[*] Clicando no primeiro resultado...")
                await page.click(".link-busca-nome >> nth=0")
                await page.wait_for_load_state("networkidle")

                # Coleta Panorama
                panorama_dados = {
                    "nome": (await page.locator("strong:has-text('Nome') + span").inner_text()).strip(),
                    "cpf": (await page.locator("strong:has-text('CPF') + span").inner_text()).strip(),
                    "localidade": (await page.locator("strong:has-text('Localidade') + span").inner_text()).strip()
                }

                main_evidence = base64.b64encode(await page.screenshot(full_page=True)).decode('utf-8')

                # Detalhamento de Recursos
                print("[*] Expandindo Recebimento de Recursos...")
                btn_recursos = page.locator("button[aria-controls='accordion-recebimentos-recursos']")
                beneficios_coletados = []

                if await btn_recursos.count() > 0:
                    await btn_recursos.click()
                    await page.wait_for_timeout(1000)

                    tabelas = page.locator("#accordion-recebimentos-recursos .responsive")
                    count_tabelas = await tabelas.count()

                    for i in range(count_tabelas):
                        tabela = tabelas.nth(i)
                        nome_beneficio = await tabela.locator("strong").first.inner_text()
                        
                        if any(x in nome_beneficio for x in ["Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família"]):
                            print(f"[*] Coletando detalhes de: {nome_beneficio}")
                            linha = tabela.locator("tbody tr").first
                            valor = await linha.locator("td").nth(3).inner_text()
                            
                            await linha.locator("text=Detalhar").click()
                            await page.wait_for_load_state("networkidle")
                            
                            evidence_detail = base64.b64encode(await page.screenshot(full_page=True)).decode('utf-8')
                            
                            beneficios_coletados.append({
                                "tipo": nome_beneficio.strip(),
                                "valor_total": valor.strip(),
                                "evidencia_base64": evidence_detail
                            })
                            await page.go_back(wait_until="domcontentloaded")

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
                # Fallback para erros inesperados de timeout ou conexão
                return {
                    "status": "error", 
                    "mensagem": "Não foi possível retornar os dados no tempo de resposta solicitado."
                }
            finally:
                await browser.close()
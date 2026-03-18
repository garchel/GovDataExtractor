import base64
import asyncio
import re
from playwright.async_api import async_playwright, expect

class PortalScraper:
    def __init__(self):
        self.url_busca = "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"

    def e_identificador_numerico(self, texto: str) -> bool:
        apenas_numeros = re.sub(r'\D', '', texto)
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

                # 1. Limpeza e Preenchimento
                await page.fill("#termo", "")

                if filtro_social:
                    print("[*] Aplicando filtro de programa social...")
                    await page.click('button[aria-controls="box-busca-refinada"]')
                    label_social = page.locator("label[for='beneficiarioProgramaSocial']")
                    await label_social.wait_for(state="visible")
                    await label_social.click(force=True)

                    # await page.click("#btnConsultarPF", force=True)
                
                await page.fill("#termo", identificador)
                await page.keyboard.press("Enter")

                # 2. SINCRONIZAÇÃO POR TOKENS (Valida se o DOM atualizou)
                print("[*] Aguardando atualização dos resultados...")
                
                # Prepara os tokens para validação (apenas para nomes)
                tokens_busca = []
                if not self.e_identificador_numerico(identificador):
                    tokens_busca = [t.upper() for t in identificador.split() if len(t) > 2]
                    print(f"[*] Tokens para validação: {tokens_busca}")

                for _ in range(30): # Até 15 segundos
                    await page.wait_for_load_state("networkidle")
                    
                    primeiro_link = page.locator(".link-busca-nome").first
                    if await primeiro_link.count() > 0:
                        nome_na_tela = (await primeiro_link.inner_text()).upper()
                        
                        # Se for CPF, não precisa tokenizar, apenas prossegue
                        if self.e_identificador_numerico(identificador):
                            break
                        
                        # Verifica se todos os tokens de pesquisa estão no nome atual
                        print(f"[*] Analisando: {nome_na_tela[:40]}...")
                        valido = True
                        for i, token in enumerate(tokens_busca, 1):
                            if token in nome_na_tela:
                                print(f"    > Checagem termo {i} - {token} - OK")
                            else:
                                valido = False
                                break # Se um token falhar, o DOM ainda é o antigo
                        
                        if valido:
                            print("[*] Resultado validado com sucesso.")
                            break
                    
                    await page.wait_for_timeout(500)

                # 3. Validação Final de Resultados
                texto_resultados = (await page.locator("#countResultados").inner_text()).strip()
                
                if "0 resultados" in texto_resultados or texto_resultados == "0":
                    if self.e_identificador_numerico(identificador):
                        return {"status": "error", "mensagem": "Não foi possível retornar os dados no tempo de resposta solicitado."}
                    else:
                        return {"status": "error", "mensagem": f"Foram encontrados 0 resultados para o termo {identificador}."}

                # 4. Acesso ao Registro
                print("[*] Clicando no primeiro resultado...")
                link_resultado = page.locator(".link-busca-nome").first
                await link_resultado.wait_for(state="visible", timeout=10000)
                await link_resultado.click()
                
                # Aguarda carregar a página de detalhes
                await page.wait_for_selector("strong:has-text('Nome')", timeout=20000)
                await page.wait_for_load_state("networkidle")

                # 5. Coleta Panorama
                panorama_dados = {
                    "nome": (await page.locator("strong:has-text('Nome') + span").inner_text()).strip(),
                    "cpf": (await page.locator("strong:has-text('CPF') + span").inner_text()).strip(),
                    "localidade": (await page.locator("strong:has-text('Localidade') + span").inner_text()).strip()
                }

                main_evidence = base64.b64encode(await page.screenshot(full_page=True)).decode('utf-8')

                # 6. Coleta de Benefícios
                print("[*] Expandindo Recebimento de Recursos...")
                beneficios_coletados = []
                btn_recursos = page.locator("button[aria-controls='accordion-recebimentos-recursos']")
                
                if await btn_recursos.count() > 0:
                    await btn_recursos.click()
                    await page.wait_for_timeout(1500)

                    tabelas = page.locator("#accordion-recebimentos-recursos .responsive")
                    for i in range(await tabelas.count()):
                        tabela = tabelas.nth(i)
                        nome_beneficio = await tabela.locator("strong").first.inner_text()
                        
                        if any(x in nome_beneficio for x in ["Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família"]):
                            print(f"[*] Coletando detalhes de: {nome_beneficio.strip()}")
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
                            await page.go_back(wait_until="networkidle")
                            # Após o go_back, precisamos re-expandir o acordeão se houver mais de um benefício
                            if await btn_recursos.get_attribute("aria-expanded") == "false":
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
                return {"status": "error", "mensagem": "Não foi possível retornar os dados no tempo de resposta solicitado."}
            finally:
                await browser.close()
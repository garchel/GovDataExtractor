import asyncio
import json
from scraper import PortalScraper

# Cores
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

def truncar_base64(obj, limite=50):
    if isinstance(obj, dict):
        return {k: truncar_base64(v, limite) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncar_base64(i, limite) for i in obj]
    elif isinstance(obj, str) and len(obj) > 100:
        if not " " in obj: 
            return obj[:limite] + "... [BASE64 TRUNCADO]"
    return obj

async def executar_cenario(titulo, identificador, filtro=False):
    bot = PortalScraper()
    print(f"\n{BOLD}{CYAN}=== {titulo} ==={RESET}")
    print(f"{YELLOW}Entrada:{RESET} {identificador} | {YELLOW}Filtro Social:{RESET} {filtro}")
    
    res = await bot.consultar(identificador, filtro_social=filtro)
    
    color = GREEN if res.get("status") == "success" else RED
        
    print(f"{BOLD}{color}Saída Recebida:{RESET}")
    print(json.dumps(truncar_base64(res), indent=2, ensure_ascii=False))
    print(f"{CYAN}{'-'*50}{RESET}")

async def run_tests():
    # 1. Sucesso (CPF)
    await executar_cenario("Cenário 1: Sucesso (CPF)", "73665649153")

    # 2. Erro (CPF Inexistente)
    await executar_cenario("Cenário 2: Erro (CPF Inexistente)", "99999999999")

    # 3. Sucesso (Nome Completo)
    await executar_cenario("Cenário 3: Sucesso (Nome)", "Paulo Victor Carvalho de Oliveira")

		# 4. Filtrado (Nome Completo + Filtro Social)
    await executar_cenario("Cenário 4: Filtrado (Nome + Social)", "Paulo Victor Carvalho de Oliveira", filtro=True)
    
    # 5. Erro (Nome Inexistente)
    await executar_cenario("Cenário 5: Erro (Nome)", "NomeInexistenteXyZ123")

    # 6. Filtrado (Sobrenome + Filtro Social)
    await executar_cenario("Cenário 6: Filtrado (Sobrenome + Social)", "Oliveira", filtro=True)
    

if __name__ == "__main__":
    asyncio.run(run_tests())
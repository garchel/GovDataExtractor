from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from scraper import PortalScraper

app = FastAPI(
    title="Portal da Transparência RPA API",
    description="API para coleta automatizada de dados de pessoas físicas no Portal da Transparência.",
    version="1.0.0"
)

# Modelo para documentação do Schema de resposta
class ScraperResponse(BaseModel):
    status: str
    identificador: Optional[str] = None
    panorama: Optional[Dict[str, str]] = None
    evidencia_principal: Optional[str] = None
    beneficios: Optional[List[Dict[str, Any]]] = None
    mensagem: Optional[str] = None

@app.get("/consultar", response_model=ScraperResponse)
async def consultar_portal(
    identificador: str = Query(..., description="CPF, NIS ou Nome completo para busca"),
    filtro_social: bool = Query(False, description="Aplicar filtro de Beneficiário de Programa Social")
):
    """
    Endpoint que aciona o robô para realizar a consulta no Portal da Transparência.
    """

    print(f"DEBUG: Recebida requisição para {identificador}")
    scraper = PortalScraper()
    try:
        resultado = await scraper.consultar(identificador, filtro_social)
        return resultado
    except Exception as e:
        return {"status": "error", "mensagem": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import re
import os
import base64

class Utils:
    @staticmethod
    def e_identificador_numerico(texto: str) -> bool:
        return len(re.sub(r'\D', '', texto)) == 11

    @staticmethod
    def gerar_caminho_evidencia(base_dir: str, nome: str, cpf: str) -> str:
        nome_slug = re.sub(r'[^\w\s-]', '', nome).strip().replace(' ', '_')
        cpf_limpo = re.sub(r'\D', '', cpf)
        caminho = os.path.join(base_dir, f"{nome_slug}_{cpf_limpo}")
        if not os.path.exists(caminho): 
            os.makedirs(caminho)
        return caminho

    @staticmethod
    def converter_para_base64(caminho_arquivo: str) -> str:
        with open(caminho_arquivo, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
            
    @staticmethod
    def slugify(texto: str) -> str:
        return re.sub(r'[^\w\s-]', '', texto).strip().replace(' ', '_')
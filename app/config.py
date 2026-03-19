class Config:
    URL_BUSCA = "https://portaldatransparencia.gov.br/pessoa-fisica/busca/lista"
    BASE_DIR = "evidencias_portal"
    
    # Seletores CSS
    INPUT_BUSCA = "#termo"
    BTN_FILTRO_REFINADO = 'button[aria-controls="box-busca-refinada"]'
    LABEL_SOCIAL = "label[for='beneficiarioProgramaSocial']"
    LINK_RESULTADO_NOME = ".link-busca-nome"
    COUNT_RESULTADOS = "#countResultados"
    BTN_RECURSOS = "button[aria-controls='accordion-recebimentos-recursos']"
    TABELAS_RECURSOS = "#accordion-recebimentos-recursos .responsive"
    
    # Seletores de Extração
    LABEL_NOME = "strong:has-text('Nome') + span"
    LABEL_CPF = "strong:has-text('CPF') + span"
    LABEL_LOCALIDADE = "strong:has-text('Localidade') + span"
    
    # Timeouts e Configurações
    TIMEOUT_PADRAO = 60000
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time

# Configurações da página (certifique-se de ter removido o 'icon="📈"')
st.set_page_config(page_title="Indicadores B3 em Tempo Real", layout="wide")
st.title("📊 Indicadores Fundamentalistas da B3 (Tempo Real)")
st.markdown("""
Esta aplicação busca dados fundamentalistas e de cotação de ações da B3 em tempo real.
Utilizamos `yfinance` para dados básicos e tentamos complementar com informações do `statusinvest.com.br`.
""")

# Campo de entrada para os tickers
st.header("Selecione ou Digite os Tickers")
st.info("Para ações da B3, utilize o sufixo '.SA' (ex: VALE3.SA, PETR4.SA).")

# Lista de tickers pré-definidos para facilitar
default_tickers = [
    "JHSF3.SA", "TRIS3.SA", "RECV3.SA", "SAPR3.SA", "BLAU3.SA", "VLID3.SA",
    "CYRE3.SA", "FIQE3.SA", "MDNE3.SA", "GRND3.SA", "CSMG3.SA", "CPLE3.SA",
    "SHUL4.SA", "VALE3.SA", "ITSA3.SA", "PRIO3.SA", "CMIG3.SA", "LAVV3.SA",
    "MILS3.SA", "KEPL3.SA", "SBSP3.SA", "POMO3.SA", "WIZC3.SA", "BRBI11.SA",
    "MULT3.SA", "ABEV3.SA", "VIVA3.SA", "VULC3.SA", "TGMA3.SA", "UNIP6.SA",
    "POMO4.SA", "CMIN3.SA", "PORT3.SA", "DIRR3.SA", "PLPL3.SA", "B3SA3.SA",
    "LEVE3.SA", "TOTS3.SA", "WEGE3.SA", "CURY3.SA", "STBP3.SA"
]

# Adicionar um campo de texto para tickers adicionais
tickers_input = st.text_area(
    "Digite tickers adicionais (um por linha, ex: BBDC4.SA):",
    value="\n".join(default_tickers)
)
tickers_list = [t.strip().upper() for t in tickers_input.split('\n') if t.strip()]

# Dicionário de mapeamento de colunas do Status Invest para nomes amigáveis
MAP_STATUS_INVEST_COLS = {
    'P/L': 'P/L', 'P/VP': 'P/VP', 'PSR': 'PSR', 'Div.Yield': 'DY', # Mantenha DY aqui
    'P/Ativo': 'P/Ativos', 'P/Cap.Giro': 'P/Cap. Giro', 'P/EBIT': 'P/EBIT',
    'P/Ativ Circ.Liq.': 'P. At Cir. Liq.', 'EV/EBIT': 'EV/EBIT',
    'Div.Líq./PL': 'Div. Liq. / Patri', 'Div.Líq./EBIT': 'Divida Liquida / EBIT',
    'Liq.Corr.': 'Liq. Corrente', 'ROIC': 'ROIC', 'ROE': 'ROE', 'ROA': 'ROA',
    'Patrim. Líq./Ativos': 'Patrimonio / Ativos', 'Passivos/Ativos': 'Passivos / Ativos',
    'Giro Ativos': 'Giro Ativos', 'M. Bruta': 'Margem Bruta',
    'M. EBIT': 'Margem EBIT', 'M. Líquida': 'Marg. Liquida',
    'VPA': 'VPA', 'LPA': 'LPA', 'CAGR Rec. 5 Anos': 'CAGR Receitas 5 Anos',
    'CAGR Lucros 5 Anos': 'CAGR Lucros 5 Anos', 'Liq. Média Diária': 'Liquidez Media Diaria',
    'Valor de Mercado': 'VALOR_DE_MERCADO', # Adicionado, pois Status Invest tem este
}

# Função para buscar dados do Status Invest
@st.cache_data(ttl=3600) # Cache os resultados por 1 hora para evitar muitas requisições
def fetch_status_invest_data(ticker_b3):
    """Tenta buscar dados fundamentalistas do Status Invest."""
    ticker_si = ticker_b3.replace(".SA", "")
    url = f"https://statusinvest.com.br/acoes/{ticker_si}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    data = {'Ticker': ticker_b3}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Preço Atual (Prioridade Status Invest para este)
        price_element = soup.find('div', title='Valor atual do ativo')
        if price_element:
            price_text = price_element.find('strong').text.replace('.', '').replace(',', '.')
            try:
                data['PRECO'] = float(price_text)
            except ValueError:
                data['PRECO'] = None # Se não conseguir converter, deixa como None

        # Tentar pegar os indicadores da tabela principal
        indicators_box = soup.find('div', class_='box-indicators')
        if indicators_box:
            for item in indicators_box.find_all('div', class_='top-info-box'):
                label_element = item.find('div', class_='title')
                value_element = item.find('strong')

                if label_element and value_element:
                    label = label_element.text.strip()
                    value_str = value_element.text.strip()

                    # Limpeza e conversão do valor
                    try:
                        # Remover separadores de milhar (pontos), substituir vírgula por ponto decimal
                        clean_value_str = value_str.replace('.', '').replace(',', '.')

                        # Verificar se é um percentual e ajustar a conversão
                        if '%' in clean_value_str:
                            value = float(clean_value_str.replace('%', '')) / 100
                        elif 'M' in clean_value_str: # Milhões
                            value = float(clean_value_str.replace('M', '')) * 1_000_000
                        elif 'B' in clean_value_str: # Bilhões
                            value = float(clean_value_str.replace('B', '')) * 1_000_000_000
                        else:
                            value = float(clean_value_str)

                        mapped_label = MAP_STATUS_INVEST_COLS.get(label, label)
                        data[mapped_label] = value
                    except ValueError:
                        data[label] = value_str # Manter como string se não puder converter
                    except Exception as e:
                        st.warning(f"Erro ao converter valor '{value_str}' para o indicador '{label}': {e}")
                        data[label] = value_str # Manter como string ou None

        return data
    except requests.exceptions.RequestException as e:
        st.warning(f"Não foi possível buscar dados do Status Invest para {ticker_b3}. Erro de Requisição: {e}")
        return {'Ticker': ticker_b3}
    except Exception as e:
        st.warning(f"Erro inesperado ao processar dados do Status Invest para {ticker_b3}. Erro: {e}")
        return {'Ticker': ticker_b3}
    finally:
        time.sleep(1) # Pequeno atraso para não sobrecarregar o servidor

# Função para buscar dados do yfinance
@st.cache_data(ttl=3600) # Cache os resultados por 1 hora
def fetch_yfinance_data(ticker_yf):
    """Busca dados de cotação e alguns fundamentalistas do Yahoo Finance."""
    try:
        ticker = yf.Ticker(ticker_yf)
        info = ticker.info

        data = {
            'Ticker': ticker_yf,
            # 'PRECO': info.get('currentPrice'), # Priorizaremos do Status Invest
            'DY_YF': info.get('dividendYield'), # Manter um DY do YF para comparação, se necessário
            'P/L_YF': info.get('forwardPE') or info.get('trailingPE'),
            'P/VP_YF': info.get('priceToBook'),
            'Marg. Liquida_YF': info.get('profitMargins'),
            'ROE_YF': info.get('returnOnEquity'),
            'ROA_YF': info.get('returnOnAssets'),
            'Liquidez Media Diaria_YF': info.get('averageDailyVolume10Day') * info.get('currentPrice') if info.get('averageDailyVolume10Day') and info.get('currentPrice') else None,
            'VALOR_DE_MERCADO_YF': info.get('marketCap'),
            'VPA_YF': info.get('bookValue'),
            'LPA_YF': info.get('trailingEps'),
        }
        return data
    except Exception as e:
        st.warning(f"Não foi possível buscar dados do Yahoo Finance para {ticker_yf}. Erro: {e}")
        return {'Ticker': ticker_yf}

# Função principal para buscar e combinar dados
def get_combined_data(tickers):
    all_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(tickers):
        status_text.text(f"Buscando dados para {ticker} ({i+1}/{len(tickers)})...")
        progress_bar.progress((i + 1) / len(tickers))

        # Dados do Status Invest (prioridade para fundamentalistas)
        si_data = fetch_status_invest_data(ticker)
        # Dados do Yahoo Finance (complementar)
        yf_data = fetch_yfinance_data(ticker)

        # Combinar os dicionários. si_data vai sobrescrever yf_data para chaves em comum.
        combined_row = {**yf_data, **si_data}
        all_data.append(combined_row)

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(all_data)

if st.button("Buscar Dados em Tempo Real"):
    if tickers_list:
        with st.spinner("Buscando dados, por favor aguarde..."):
            df_final = get_combined_data(tickers_list)

            # Reordenar as colunas e garantir que todas as colunas desejadas existam
            # Assegura que colunas do Status Invest (sem _SI) têm prioridade.
            desired_columns_order = [
                'Ticker', 'PRECO', 'DY', 'P/L', 'P/VP', 'P/Ativos', 'Margem Bruta',
                'Margem EBIT', 'Marg. Liquida', 'P/EBIT', 'EV/EBIT',
                'Divida Liquida / EBIT', 'Div. Liq. / Patri', 'PSR',
                'P/Cap. Giro', 'P. At Cir. Liq.', 'Liq. Corrente', 'ROE', 'ROA', 'ROIC',
                'Patrimonio / Ativos', 'Passivos / Ativos', 'Giro Ativos',
                'CAGR Receitas 5 Anos', 'CAGR Lucros 5 Anos',
                'Liquidez Media Diaria', 'VPA', 'LPA', 'PEG Ratio', 'VALOR_DE_MERCADO'
            ]
            
            # Garante que todas as colunas da ordem desejada estejam no DataFrame,
            # preenchendo com None se não existirem
            for col in desired_columns_order:
                if col not in df_final.columns:
                    df_final[col] = None
            
            # Reordena o DataFrame
            df_final = df_final[desired_columns_order]

            # Formatação final para exibição
            # Aplica a formatação APENAS se o valor não for None/NaN
            for col in df_final.columns:
                if col in ['DY', 'Margem Bruta', 'Margem EBIT', 'Marg. Liquida', 'ROE', 'ROA', 'ROIC',
                            'Patrimonio / Ativos', 'Passivos / Ativos', 'Giro Ativos',
                            'CAGR Receitas 5 Anos', 'CAGR Lucros 5 Anos']:
                    # Estes valores já devem ter vindo como decimal (ex: 0.0723 para 7.23%)
                    df_final[col] = df_final[col].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/D")
                elif col in ['PRECO', 'Liquidez Media Diaria', 'VALOR_DE_MERCADO']:
                    df_final[col] = df_final[col].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "N/D")
                elif col in ['P/L', 'P/VP', 'P/Ativos', 'PSR', 'P/EBIT', 'EV/EBIT',
                             'Divida Liquida / EBIT', 'Div. Liq. / Patri', 'P/Cap. Giro',
                             'P. At Cir. Liq.', 'Liq. Corrente', 'VPA', 'LPA', 'PEG Ratio']:
                    df_final[col] = df_final[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/D")


            st.success("Busca de dados concluída!")
            st.dataframe(df_final, use_container_width=True, height=700) # Tabela ajusta à largura e tem altura fixa
            st.markdown("---")
            st.caption("Os dados são coletados de fontes públicas (Yahoo Finance e Status Invest). A precisão e a completude podem variar. Dados de CAGR e PEG Ratio são difíceis de obter gratuitamente em tempo real e podem estar ausentes.")

    else:
        st.warning("Por favor, digite ou selecione pelo menos um ticker.")

st.sidebar.header("Dicas")
st.sidebar.info("""
- Os dados podem ter um pequeno atraso.
- A completude das informações depende da disponibilidade nas fontes gratuitas.
- Adicione ou remova tickers na caixa de texto acima.
""")

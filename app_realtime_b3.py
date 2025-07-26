import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time # Para adicionar um pequeno delay entre as requisições, evitando bloqueios

# Configurações da página
st.set_page_config(page_title="Indicadores B3 em Tempo Real", layout="wide", icon="📈")
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
    'P/L': 'P/L', 'P/VP': 'P/VP', 'PSR': 'PSR', 'Div.Yield': 'DY',
    'P/Ativo': 'P/Ativos', 'P/Cap.Giro': 'P/Cap. Giro', 'P/EBIT': 'P/EBIT',
    'P/Ativ Circ.Liq.': 'P. At Cir. Liq.', 'EV/EBIT': 'EV/EBIT',
    'Div.Líq./PL': 'Div. Liq. / Patri', 'Div.Líq./EBIT': 'Divida Liquida / EBIT',
    'Liq.Corr.': 'Liq. Corrente', 'ROIC': 'ROIC', 'ROE': 'ROE', 'ROA': 'ROA',
    'Patrim. Líq./Ativos': 'Patrimonio / Ativos', 'Passivos/Ativos': 'Passivos / Ativos',
    'Giro Ativos': 'Giro Ativos', 'M. Bruta': 'Margem Bruta',
    'M. EBIT': 'Margem EBIT', 'M. Líquida': 'Marg. Liquida',
    'VPA': 'VPA', 'LPA': 'LPA', 'CAGR Rec. 5 Anos': 'CAGR Receitas 5 Anos',
    'CAGR Lucros 5 Anos': 'CAGR Lucros 5 Anos', 'Liq. Média Diária': 'Liquidez Media Diaria',
    # Adicione mais mapeamentos conforme necessário se o yfinance ou o statusinvest usarem nomes diferentes
}

# Função para buscar dados do Status Invest
@st.cache_data(ttl=3600) # Cache os resultados por 1 hora para evitar muitas requisições
def fetch_status_invest_data(ticker_b3):
    """Tenta buscar dados fundamentalistas do Status Invest."""
    # O ticker no Status Invest não tem o '.SA'
    ticker_si = ticker_b3.replace(".SA", "")
    url = f"https://statusinvest.com.br/acoes/{ticker_si}"
    headers = {'User-Agent': 'Mozilla/5.0'} # Simula um navegador

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Lança um erro para status de erro HTTP
        soup = BeautifulSoup(response.content, 'html.parser')

        data = {'Ticker': ticker_b3}

        # Tentar pegar o preço atual - pode estar em vários lugares
        price_element = soup.find('div', title='Valor atual do ativo')
        if price_element:
            price_text = price_element.find('strong').text.replace('.', '').replace(',', '.')
            data['PRECO'] = float(price_text)
        else:
            data['PRECO'] = None

        # Tentar pegar os indicadores da tabela principal
        # Os indicadores no Status Invest estão dentro de divs com data-controller="boxes"
        # e os valores são strong dentro de div class="value"
        # Isso é uma tentativa e pode quebrar se o HTML mudar.
        indicators_box = soup.find('div', class_='box-indicators')
        if indicators_box:
            for item in indicators_box.find_all('div', class_='top-info-box'):
                label_element = item.find('div', class_='title')
                value_element = item.find('strong')

                if label_element and value_element:
                    label = label_element.text.strip()
                    value_str = value_element.text.strip().replace('.', '').replace(',', '.')
                    try:
                        # Tentar converter para float, remover % se houver
                        if '%' in value_str:
                            value = float(value_str.replace('%', '')) / 100
                        else:
                            value = float(value_str)
                        # Mapear para o nome da coluna desejado
                        mapped_label = MAP_STATUS_INVEST_COLS.get(label, label)
                        data[mapped_label] = value
                    except ValueError:
                        data[label] = value_str # Manter como string se não puder converter

        # Tentar pegar VPA e LPA de outra seção (geralmente tabela de DRE/BP)
        # Esta parte é mais difícil e pode variar muito. Como o yfinance já tem VPA/LPA.
        # Por simplicidade, vou priorizar yfinance para esses.

        return data
    except requests.exceptions.RequestException as e:
        st.warning(f"Não foi possível buscar dados do Status Invest para {ticker_b3}. Erro: {e}")
        return {'Ticker': ticker_b3} # Retorna apenas o ticker se houver erro
    except Exception as e:
        st.warning(f"Erro ao processar dados do Status Invest para {ticker_b3}. Erro: {e}")
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
            'PRECO': info.get('currentPrice'),
            'DY': info.get('dividendYield'),
            'P/L': info.get('forwardPE') or info.get('trailingPE'),
            'P/VP': info.get('priceToBook'),
            'Marg. Liquida': info.get('profitMargins'),
            'ROE': info.get('returnOnEquity'),
            'ROA': info.get('returnOnAssets'),
            'Liquidez Media Diaria': info.get('averageDailyVolume10Day') * info.get('currentPrice'), # Aproximação
            'VALOR_DE_MERCADO': info.get('marketCap'),
            'VPA': info.get('bookValue'),
            'LPA': info.get('trailingEps'),
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

        # Dados do Yahoo Finance (mais estável para preço e alguns básicos)
        yf_data = fetch_yfinance_data(ticker)

        # Dados do Status Invest (tentativa de complementar fundamentalistas)
        si_data = fetch_status_invest_data(ticker)

        # Combinar os dicionários. si_data pode sobrescrever yf_data se tiver campos em comum.
        # Preferimos os dados do SI para fundamentalistas se disponíveis e convertidos corretamente
        combined_row = {**yf_data, **si_data}
        all_data.append(combined_row)

    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(all_data)

if st.button("Buscar Dados em Tempo Real"):
    if tickers_list:
        with st.spinner("Buscando dados, por favor aguarde..."):
            df_final = get_combined_data(tickers_list)

            # Reordenar as colunas para seguir a ordem desejada ou similar
            # Garantir que todas as colunas estejam no DataFrame para evitar KeyError
            # Aqui você define a ordem exata das colunas que você quer ver
            desired_columns_order = [
                'Ticker', 'PRECO', 'DY', 'P/L', 'P/VP', 'P/Ativos', 'Margem Bruta',
                'Margem EBIT', 'Marg. Liquida', 'P/EBIT', 'EV/EBIT',
                'Divida Liquida / EBIT', 'Div. Liq. / Patri', 'PSR',
                'P/Cap. Giro', 'P. At Cir. Liq.', 'Liq. Corrente', 'ROE', 'ROA', 'ROIC',
                'Patrimonio / Ativos', 'Passivos / Ativos', 'Giro Ativos',
                'CAGR Receitas 5 Anos', 'CAGR Lucros 5 Anos',
                'Liquidez Media Diaria', 'VPA', 'LPA', 'PEG Ratio', 'VALOR_DE_MERCADO'
            ]
            # Adiciona colunas que podem estar no df_final mas não na lista de desejadas
            final_columns = [col for col in desired_columns_order if col in df_final.columns]
            for col in df_final.columns:
                if col not in final_columns and col not in desired_columns_order:
                    final_columns.append(col) # Adiciona qualquer coluna extra no final

            df_final = df_final[final_columns]

            # Formatação final para exibição
            # Aplica a formatação APENAS se o valor não for None/NaN
            for col in df_final.columns:
                if col in ['DY', 'Margem Bruta', 'Margem EBIT', 'Marg. Liquida', 'ROE', 'ROA', 'ROIC',
                            'Patrimonio / Ativos', 'Passivos / Ativos', 'Giro Ativos',
                            'CAGR Receitas 5 Anos', 'CAGR Lucros 5 Anos']:
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

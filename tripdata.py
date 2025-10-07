#%%
import pandas as pd
import duckdb
import requests
import zipfile
import io
import json
import re
import boto3
from botocore import UNSIGNED
from botocore.config import Config
import matplotlib.pyplot as plt

URL_BASE = "https://divvy-tripdata.s3.amazonaws.com/"
URL_INDEX = URL_BASE + "index.html"

BUCKET_NAME="divvy-tripdata"

def listar_arquivos_disponiveis():
    s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

    arquivos = []
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get('Contents', []):
            nome = obj['Key'].split('/')[-1]
            if obj['Key'].endswith('.zip') and not nome.startswith('Divvy_'):
                arquivos.append(obj['Key'])

    return sorted(arquivos)

def carregar_controle(caminho_arquivo='controle.json'):
    try:
        with open(caminho_arquivo, 'r') as f:
            controle = json.load(f)
    except FileNotFoundError:
        controle = {"ultimo_arquivo": ""}
    return controle

def atualizar_controle(arquivo, caminho_arquivo='controle.json'):
    controle = {"ultimo_arquivo": arquivo}
    with open(caminho_arquivo, 'w') as f:
        json.dump(controle, f)

def baixar_e_processar(url):        
    response = requests.get(url)
    zip_file = io.BytesIO(response.content)

    with zipfile.ZipFile(zip_file, 'r') as z:
        # listar todos os arquivos no zip
        csv_files = [f for f in z.namelist() if f.endswith('.csv')]
        if not csv_files:
            raise ValueError("Nenhum arquivo CSV encontrado no arquivo zip.")
        
        # ler o primeiro arquivo CSV encontrado
        with z.open(csv_files[0]) as f:
            df = pd.read_csv(f)

    # faz o tratamento dos dados
    df.dropna(inplace=True)
    df['started_at'] = pd.to_datetime(df['started_at'])
    df['ended_at'] = pd.to_datetime(df['ended_at'])

    tipo_traduzido = {'classic_bike': 'Bicicleta Clássica',
                      'electric_bike': 'Bicicleta Elétrica'}

    df['rideable_type'] = df['rideable_type'].map(tipo_traduzido)
    return df

arquivos = listar_arquivos_disponiveis()

ultimo = carregar_controle().get("ultimo_arquivo", "") # último arquivo processado
novos = [a for a in arquivos if a > ultimo] if ultimo else arquivos # arquivos novos para processar

# processa o arquivo mais recente
df = pd.DataFrame()
if novos:
    novo_arquivo = novos[-1]

    df = baixar_e_processar(URL_BASE + novo_arquivo)
    atualizar_controle(novo_arquivo)
    print(f"Processado o novo arquivo: {novo_arquivo}")
else:
    print("Nenhum novo arquivo para processar.")
    novo_arquivo = ultimo

print(f"Total de registros no DataFrame: {len(df)}")
#%%
# calcular o mês e ano do arquivo processado
match = re.search(r'(\d{4})(\d{2})', novo_arquivo)
if match:
    ano, mes_num = match.groups()
    meses_nome = {
        '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
        '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
        '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
    }
    mes = meses_nome.get(mes_num, 'Mês Inválido')    
    print(f"Mês/Ano do arquivo processado: {mes}/{ano}")
else:
    print("Não foi possível extrair o mês e ano do nome do arquivo.")    
#%%    
# carregar os dados em um banco de dados DuckDB
con = duckdb.connect()
con.register('trips', df)

# consulta as 15 estações de início mais populares
result = con.execute("""
                     SELECT start_station_name, count(*) as count
                       FROM trips 
                      WHERE start_station_name <> 'None'
                      GROUP BY start_station_name 
                      ORDER BY COUNT(*) DESC 
                     LIMIT 15""").fetchdf()

# plotar os resultados
plt.figure(figsize=(10,6))
plt.barh(result['start_station_name'], result['count'], color='skyblue')
plt.xlabel('Número de Viagens')
plt.ylabel('Estação de Início')
plt.title(f'Top 15 Estações de Início de Viagens de Bicicleta em Chicago ({mes}/ {ano})')
plt.gca().invert_yaxis()  # inverter o eixo y para ter a estação com mais viagens no topo
plt.show()
#%%
# com plotly
import plotly.express as px
#import streamlit as st
#st.title('Análise de Dados de Viagens de Bicicleta em Chicago')
#st.write(f'Total de registros no DataFrame: {len(df)}')
# top 15 estações de início mais populares
fig1 = px.bar(result,
                x='count', 
                y='start_station_name', 
                orientation='h',
                title=f'Top 15 Estações de Início de Viagens de Bicicleta em Chicago ({mes}/ {ano})',
                labels={'count': 'Número de Viagens', 'start_station_name': 'Estação de Início'},
                color_discrete_sequence=['skyblue']*15)
fig1.update_yaxes(categoryorder='total ascending')
fig1.show()
#st.plotly_chart(fig1)


#%%
result = con.execute("""
                        SELECT
                            rideable_type,
                            started_at,
                            ended_at,
                            ROUND(EXTRACT(EPOCH FROM ended_at - started_at) / 3600.0, 2) AS duracao_horas
                        FROM
                            trips
                        LIMIT 15
                        """).fetchdf()
print(result.head())

#%%
# consulta a duração média das viagens por tipo de bicicleta
result = con.execute("""
                        SELECT 
                            rideable_type,
                            AVG(ended_at - started_at) AS avg_duration_seconds
                        FROM
                            trips
                        GROUP BY
                            rideable_type
                        ORDER BY
                            avg_duration_seconds DESC
                        """).fetchdf()

# plotar os resultados
plt.figure(figsize=(8,5))
plt.bar(result['rideable_type'], result['avg_duration_seconds'] / 60, color='salmon')
plt.xlabel('Tipo de Bicicleta')
plt.ylabel('Duração Média (minutos)')
plt.title('Duração Média das Viagens por Tipo de Bicicleta')
plt.show()
#%%

# consulta o número total de viagens por tipo de bicicleta
result = con.execute("""
                        SELECT 
                            rideable_type,
                            COUNT(*) AS total_trips
                        FROM
                            trips
                        GROUP BY
                            rideable_type
                        ORDER BY    
                            total_trips DESC
                        """).fetchdf()  

# plotar os resultados
plt.figure(figsize=(8,5))
plt.bar(result['rideable_type'], result['total_trips'], color='lightgreen')
plt.xlabel('Tipo de Bicicleta')
plt.ylabel('Número Total de Viagens')
plt.title('Número Total de Viagens por Tipo de Bicicleta')
plt.show()
#%%

# consulta a duração média das viagens por dia da semana
result = con.execute("""
                        SELECT 
                            DATE_PART('dow', started_at) AS dia_semana_num,
                            CASE DATE_PART('dow', started_at)
                                WHEN 0 THEN 'domingo'
                                WHEN 1 THEN 'segunda-feira'
                                WHEN 2 THEN 'terça-feira'
                                WHEN 3 THEN 'quarta-feira'
                                WHEN 4 THEN 'quinta-feira'
                                WHEN 5 THEN 'sexta-feira'
                                WHEN 6 THEN 'sábado'
                            END AS dia_semana,

                            AVG(ended_at - started_at) AS avg_duration_seconds
                        FROM
                            trips
                        GROUP BY
                            dia_semana_num, dia_semana
                        ORDER BY
                            dia_semana_num
                        """).fetchdf()
# plotar os resultados
plt.figure(figsize=(10,6))
plt.bar(result['dia_semana'], result['avg_duration_seconds'] / 60, color='orchid')
plt.xlabel('Dia da Semana')
plt.ylabel('Duração Média (minutos)')
plt.title('Duração Média das Viagens por Dia da Semana')
plt.show()
#%%
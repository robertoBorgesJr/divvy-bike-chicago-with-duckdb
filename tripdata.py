#%%
import pandas as pd
import duckdb
import requests
import zipfile
import io
import matplotlib.pyplot as plt

# URL dos dados de bicicletas de Chicago (Divvy Trips)
DATA_URL = "https://divvy-tripdata.s3.amazonaws.com/202509-divvy-tripdata.zip"

# baixar e extrair o arquivo zip
response = requests.get(DATA_URL)
zip_file = io.BytesIO(response.content)

with zipfile.ZipFile(zip_file, 'r') as z:
    # listar todos os arquivos no zip
    csv_files = [f for f in z.namelist() if f.endswith('.csv')]
    if not csv_files:
        raise ValueError("Nenhum arquivo CSV encontrado no arquivo zip.")
    
    # ler o primeiro arquivo CSV encontrado
    with z.open(csv_files[0]) as f:
        df = pd.read_csv(f)

#%%
#print(df.info())
#%%
#print(df.head())
#%%
# faz o tratamento dos dados
df.dropna(inplace=True)
df['started_at'] = pd.to_datetime(df['started_at'])
df['ended_at'] = pd.to_datetime(df['ended_at'])

tipo_traduzido = {'classic_bike': 'Bicicleta Clássica',
                  'electric_bike': 'Bicicleta Elétrica'}

df['rideable_type'] = df['rideable_type'].map(tipo_traduzido)

#%%
# carregar os dados em um banco de dados DuckDB
con = duckdb.connect()
con.register('trips', df)

#%%
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
plt.title('Top 15 Estações de Início de Viagens de Bicicleta em Chicago (Outubro/2025)')
plt.gca().invert_yaxis()  # inverter o eixo y para ter a estação com mais viagens no topo
plt.show()
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
#%%
import boto3
from botocore import UNSIGNED
from botocore.config import Config

bucket_name="divvy-tripdata"
prefix="2023/"

# Cliente S3 sem autenticação
s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    
arquivos = []
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=bucket_name):
    for obj in page.get('Contents', []):
        nome = obj['Key'].split('/')[-1]
        if obj['Key'].endswith('.zip') and not nome.startswith('Divvy_'):
            arquivos.append(obj['Key'])
    
arquivos = sorted(arquivos)

print(f"Total de arquivos ZIP encontrados: {len(arquivos)}")

for a in arquivos:
    print(a)

#%%
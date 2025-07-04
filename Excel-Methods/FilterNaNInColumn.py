import pandas as pd
import numpy as np

df = pd.DataFrame([[1,np.nan,'A100'],[4,5,'A213'],[7,8,np.nan],[10,np.nan,'GA23']])
df.columns = ['areaCode','Distance','accountCode']
print(df)
#print(df.isnull().sum())
df_1=df.dropna(subset=['Distance'])
print(df_1)

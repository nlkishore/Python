import pandas as pd
from openpyxl import load_workbook
import os.path
import sys
sys.path.append('C:/Python/ConfigReader')
import PropReader as pReader
import numpy as np


def compareDataFrames(df1,df2):
    df1=pd.read_csv('C:\Python/Resources/file1.csv')
    df2=pd.read_csv('C:\Python/Resources/file2.csv')
    A = pd.merge(df1,df2, on='name', how='inner')
    B = A.copy()
    B['dept_x'] = A.apply(lambda x : 'mismatch' if x.dept_x!=x.dept_y else x.dept_x, axis=1)
    print(B)


def compareDF():
    # or if you want to do it on all columns except the first two because there's too many
    df1=pd.read_csv('C:/Python/Resources/file1.csv')
    print(df1)
    df2=pd.read_csv('C:/Python/Resources/file2.csv')
    print(df2)
    A = pd.merge(df1,df2, on='name', how='inner')
    print(A)
    cols = [a for a in df1.columns if a not in ['name','id']]
    print(cols)
    
    C = A.copy()
    C[cols] = C.apply(is_mismatch(), axis=1) # don't forget that axis=1 here !
    def is_mismatch(x) :
        L = ['mismatch' if x[cols[i]+'_x']!=x[cols[i]+'_y'] else x[cols[i]+'_x'] for i in range(len(cols))]
        return pd.Series(L)
    print(C)
# define a function that compares for all columns


'''def is_mismatch(x,cols) :
    L = ['mismatch' if x[cols[i]+'_x']!=x[cols[i]+'_y'] else x[cols[i]+'_x'] for i in range(len(cols))]
    return pd.Series(L)'''


def diff_pd(df1, df2):
    """Identify differences between two pandas DataFrames"""
    assert (df1.columns == df2.columns).all(), \
        "DataFrame column names are different"
    if any(df1.dtypes != df2.dtypes):
        "Data Types are different, trying to convert"
        df2 = df2.astype(df1.dtypes)
    if df1.equals(df2):
        return None
    else:
        # need to account for np.nan != np.nan returning True
        diff_mask = (df1 != df2) & ~(df1.isnull() & df2.isnull())
        ne_stacked = diff_mask.stack()
        changed = ne_stacked[ne_stacked]
        changed.index.names = ['id', 'col']
        difference_locations = np.where(diff_mask)
        changed_from = df1.values[difference_locations]
        changed_to = df2.values[difference_locations]
        return pd.DataFrame({'from': changed_from, 'to': changed_to},
                            index=changed.index)

def diff_df(df1, df2, how="left"):
    """
      Find Difference of rows for given two dataframes
      this function is not symmetric, means
            diff(x, y) != diff(y, x)
      however
            diff(x, y, how='left') == diff(y, x, how='right')

      Ref: https://stackoverflow.com/questions/18180763/set-difference-for-pandas/40209800#40209800
    """
    if (df1.columns != df2.columns).any():
        raise ValueError("Two dataframe columns must match")

    if df1.equals(df2):
        return None
    elif how == 'right':
        return pd.concat([df2, df1, df1]).drop_duplicates(keep=False)
    elif how == 'left':
        return pd.concat([df1, df2, df2]).drop_duplicates(keep=False)
    else:
        raise ValueError('how parameter supports only "left" or "right keywords"')  

if __name__ == '__main__':
    df1=pd.read_csv('C:/Python/Resources/file1.csv')
    print(df1)
    df2=pd.read_csv('C:/Python/Resources/file2.csv')
    print(df2)
    #print(diff_pd(df1, df2))
    '''print(df1.compare(df2))
    print(df1.compare(df2, keep_equal=True, keep_shape=True) )
    print(df1.compare(df2, align_axis='index'))
    print(df1.compare(df2, keep_equal=True, keep_shape=True,align_axis='index'))
    #compareDF()'''
    #print(diff_df(df1, df2,'left'))
    print(diff_df(df1, df2,how="left"))

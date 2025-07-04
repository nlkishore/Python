import pandas as pd
from openpyxl import load_workbook
import os.path
#import PropReader as pReader
import sys
sys.path.append('C:/Python/ConfigReader')
import PropReader as pReader

def updateExistingExcel(df,fileName):
    #print(pReader.readConfigValue('wiki','username'))
    df=pd.read_csv('C:/Python/data.csv.txt')
    #print(df)
    if os.path.isfile(fileName):
        book = load_workbook(fileName)
        writer = pd.ExcelWriter(fileName, engine='openpyxl') 
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
        df.to_excel(writer, index=None, header=True)
        writer.save()
    else:
        df.to_excel(fileName, index=None, header=True)

def readCSVAndWriteExcel():
    read_file = pd.read_csv('C:/Python/data.csv.txt')
    read_file.to_excel('Masterfile.xlsx', index=None, header=True)
updateExistingExcel(pd.DataFrame(),'Masterfile.xlsx')
#readCSVAndWriteExcel()
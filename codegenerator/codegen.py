import time
import sys
import os
from datetime import datetime
sys.path.insert(1, 'C:/Python/ConfigReader/')
import PropReader as propreader
import glob
import shutil

def springBootBase():
    print('Test ')
    try:
        listFolders=propreader.readConfigValue('spring','folderlist')
        lstTemp=listFolders.split(',')
        baseFolder=propreader.readConfigValue('spring','basefolder')
        print(baseFolder)
        projectName=propreader.readConfigValue('spring','projectname')
        print(listFolders)
        srcCodeFolder=propreader.readConfigValue('spring','srcfolder')
        print(srcCodeFolder)
        if (not os.path.exists(baseFolder+'/'+projectName)):
            os.makedirs(baseFolder+'/'+projectName)
        if (not os.path.exists(baseFolder+'/'+projectName+'/'+srcCodeFolder)):
            os.makedirs(baseFolder+'/'+projectName+'/'+srcCodeFolder)
        for x in lstTemp:
            print(' from Lst' +x)
            fldrPath=propreader.readConfigValue('spring',x)
            print('folder Path '+fldrPath)
            fullPath=baseFolder+'/'+projectName+'/'+srcCodeFolder+'/'+fldrPath
            print('full Path '+fullPath)
            if (not os.path.exists(fullPath)):
                os.makedirs(fullPath)
            createSrcFileTemplate(fullPath,fldrPath,x)


    except Exception as ex:
        print(str(ex))

def createSrcFileTemplate(fullPath,fldrPath,fldrPathKey):
    pkgName=fldrPath.replace('\\','.')
    filePathKey=''
    try:
        print('filePathKey  before'+fldrPathKey)
        filePathKey=fldrPathKey.replace('folder','filename')
        print('filePathKey '+filePathKey)
        if('filename' in filePathKey):
            fileNametmp=propreader.readConfigValue('spring',filePathKey)
            fileNameLst = fileNametmp.split(',')
            for fileName in fileNameLst:
                print('FileName '+fileName)
                print('FileName full path '+fullPath+"/"+fileName)
                f = open(fullPath+"/"+fileName, "a")
                f.write("package "+pkgName+ ";\n")
                f.write("public class "+fileName.replace('.java','')+ " {}")
                f.close()
    except Exception as ex:
        print(ex)
    
    


if __name__ == "__main__":   
    springBootBase()


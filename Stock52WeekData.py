from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import sys
import os
from datetime import datetime
sys.path.insert(1, 'C:/Python/ConfigReader/')
import PropReader as propreader
import glob
import shutil

def accessAmazon():
    for i in range(20):
        # create instance of Chrome webdriver
        try:
            driver=webdriver.Chrome() 
            driver.get("https://www.amazon.in/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.in%2Fgp%2Fcss%2Fhomepage.html%3Ffrom%3Dhz%26ref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=inflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&")
            driver.find_element("id", "ap_email").send_keys('xxxx6126')
            driver.find_element("id", "continue").click()
            time.sleep(10)
            driver.find_element("id", "auth-fpp-link-bottom").click()
            driver.find_element("id", "continue").click()
            # set the interval to send each sms
            time.sleep(400)
        except Exception as ex:
            print (ex)   
            continue     
    
        # Close the browser
        #driver.close()
def yahooDownload(stockSymbol):
    baseFolder =  propreader.readConfigValue('brok','bfolder')
    downLodFolder = propreader.readConfigValue('brok','dfolder')
    subFolder=datetime.now().strftime('%Y%m%d')
    fullPath=baseFolder+'/'+stockSymbol+'/'+subFolder
    print(baseFolder)
    print(downLodFolder)
    if not (os.path.exists):
        os.makedirs(fullPath, exist_ok=True)
    #https://finance.yahoo.com/quote/TSLA/history?p=TSLA
    driver = getDriver1()
    driver.get("https://finance.yahoo.com/quote/TSLA/history?p="+stockSymbol)
    time.sleep(10)
    element = driver.find_element(By.XPATH, "//span[contains(text(),'Download')]")
    element.click()
    time.sleep(20)
    print(downLodFolder+stockSymbol+'*')
    files = glob.glob(downLodFolder+stockSymbol+'*')
    print(files)
    latest_file = max(files, key=os.path.getctime)
    shutil.copy2(latest_file,fullPath)

def getDriver():
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory" : "PATH"}
    prefs = {"driver" : "C:/ChromeDriver/chrome-win64/chrome.exe"}
    options.add_experimental_option("prefs",prefs)
    driver = webdriver.Chrome(options=options)
    #driver = webdriver.Chrome('C:/Users/HP/Desktop/Drivers/chromedriver_win32/chromedriver.exe')

def getDriver1():
    options = webdriver.ChromeOptions()
    options.binary_location = "C:/ChromeDriver/chrome-win64/chrome.exe"
    options.add_argument ("download.default_directory=C:/Your_Directory")
    driver = webdriver.Chrome(options)
    return driver

def getDriver2():
    from selenium.webdriver import Chrome, ChromeOptions
    prefs = {
        "download.default_directory": "C:/StockHistoricData/",
        "download.directory_upgrade": True,
        "download.prompt_for_download": False,
    }
    chromeOptions = ChromeOptions()
    chromeOptions.add_experimental_option("prefs", prefs)
    driver = Chrome(options=chromeOptions)
    return driver
if __name__ == "__main__":
    yahooDownload(sys.argv[1])
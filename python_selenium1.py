from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

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
def yahooDownload():
    #https://finance.yahoo.com/quote/TSLA/history?p=TSLA
    driver=webdriver.Chrome() 
    driver.get("https://finance.yahoo.com/quote/TSLA/history?p=TSLA")
    time.sleep(10)
    element = driver.find_element(By.XPATH, "//span[contains(text(),'Download')]")
    element.click()
    time.sleep(300)
 
yahooDownload()
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener

#from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from pynput.mouse import Listener

b = webdriver.Chrome()
b.maximize_window()


class EventListeners(AbstractEventListener):
    def before_navigate_to(self, url, driver):
        print("before_navigate_to %s" % url)

    def after_navigate_to(self, url, driver):
        print("after_navigate_to %s" % url)

    def before_click(self, element, driver):
        print("before_click %s" % element)

    def after_click(self, element, driver):
        print("after_click %s" %element)

    def after_navigate_forward(self, driver):
        print("after_navigate_forward");

    def before_navigate_forward(self, driver):
        print("before_navigate_forward")

    def after_navigate_back(self, driver):
        print("after_navigate_back")

    def before_navigate_back(self, driver):
        print("before_navigate_back")

    def before_change_value_of(self, element, driver):
        print("before_change_value_of")

d = EventFiringWebDriver(b,EventListeners())

d.get('https://www.cnn.com')
d.implicitly_wait(20)
d.get('https://www.google.de')
d.implicitly_wait(60)
d.back()

def on_click(x, y, button, pressed):
    if pressed:
        print('Mouse clicked')
        time.sleep(2)
        print("Navigation to: %s " % b.current_url)

with Listener(on_click=on_click) as listener:
    listener.join()
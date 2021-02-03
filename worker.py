import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import re
from enum import Enum

class Signal(Enum):
    BUY = 0,
    LIST = 1,
    DELIST = 2

class Worker:
    def __init__(self, name, account, password):
        self.is_busy = False
        self.name = name
        self.account = account
        self.password = password
        self.username = ""
        capa = DesiredCapabilities.CHROME
        capa["pageLoadStrategy"] = "eager"
        self.driver = webdriver.Chrome(desired_capabilities=capa)
        self.wait = WebDriverWait(self.driver, 60)

    def launch(self):
        self.is_busy = True
        self.driver.get("https://www.nbatopshot.com/marketplace")

        # 登陆到dapper
        try:
            login_element = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(),'Log In')]"))
            )
            login_element.click()
            # email
            element_email = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@id='email']"))
            )
            element_email.send_keys(self.account)
            # password
            self.driver.find_element_by_xpath(
                "//input[@id='password']").send_keys(self.password)
            # login
            self.driver.find_element_by_xpath("//button[@id='login']").click()
            user_name_link = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'/user/')]"))
            )
            user_name_href = user_name_link.get_attribute('href')
            regex = re.compile(r'@(\w+)')
            mo = regex.search(user_name_href)
            self.username = mo.group(1)
            print('登陆账号成功')
        except Exception as e:
            print(f"登陆时出错，错误为{e}")
            # TODO 尝试重新登陆
            self.driver.close()
        finally:  
            self.is_busy = False

    def dispatcher(self, signal_index, args):
        '''
            BUY = 0,
            LIST = 1,
            DELIST = 2
        '''
        signal = int(signal_index)
        if signal == 0:
            self.buy(*args)
        elif signal == 1:
            self.list_moment(*args)
        elif signal == 2:
            self.delist_moment(args[0])
        else:
            print(f'无法解析信号:{signal}')

    def buy(self, set_ID, play_ID, serial_number):
        if not (set_ID or play_ID or serial_number):
            print('请输入set_ID/play_ID/serial_number')
            return

        moment_listings_url = f"https://www.nbatopshot.com/listings/p2p/{set_ID}+{play_ID}?serialNumber={serial_number}"

        try:
            self.is_busy = True
            self.driver.execute_script("window.open('');")
            tab = self.driver.window_handles[-1]
            self.driver.switch_to.window(tab)
            self.driver.get(moment_listings_url)    
            # 瞬间页里点击购买
            element_buy = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[@data-testid='button-p2p-purchase-moment']/span[text()[contains(.,'Buy for')]]"))
            )
            self.driver.execute_script("window.scrollBy(0,100)")
            # 点不到的滚轮下滑页面
            result = None
            while result is None:
                try:
                    element_buy.click()
                    result = True
                except:
                    self.driver.execute_script("window.scrollBy(0,100)")
                    pass
            # dapper里点击购买
            element_dapper_pay = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button.css-u0hnk9'))
            )
            element_dapper_pay.click()
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//span[@class='Label-sc-1c0wex9-0 bpIweo']"))
            )
        except Exception as e:
            print(f'购买 {set_ID}+{play_ID}?serialNumber={serial_number} 失败, 错误是{e}')
        finally:
            self.driver.close()
            self.switch_to_tab(0)
            self.is_busy = False
            return

    def list_moment(self, moment_id, targetPrice):
        if not (moment_id or targetPrice):
            print('请输入moment_id/targetPrice')
            return
        try:
            self.is_busy = True
            moment_url = f"https://www.nbatopshot.com/moment/{self.username}+{moment_id}"

            self.open_new_tab()     
            self.driver.get(moment_url)

            place_for_sale_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(),'Place for sale')]"))
            )
            place_for_sale_button.click()
            price_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@id='price']"))
            )
            price_input.send_keys(targetPrice)
            time.sleep(1)
            submit_sale_button = self.driver.find_element_by_xpath("//button[@type='submit']")
            submit_sale_button.click()
            confirm_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Confirm')]"))
            )
            confirm_button.click()
            time.sleep(1)
            self.driver.close()
            print(f"上架完成，回到准备状态")
        except Exception:
            print(f'上架 {moment_id} 出现异常')
        finally:
            self.driver.close()
            time.sleep(1)
            self.switch_to_tab(1)
            self.driver.close()
            time.sleep(1)
            self.switch_to_tab(0)
            self.is_busy = False
            return

    def delist_moment(self, moment_id):
        if not moment_id:
            print('请输入下架的moment_id')
            return  
        try:
            self.is_busy = True

            moment_url = f"https://www.nbatopshot.com/moment/{self.username}+{moment_id}"

            self.open_new_tab()
            self.driver.get(moment_url)

            cancel_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[contains(text(),'Cancel Sale')]"))
            )
            cancel_button.click()
            confirm_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Confirm')]"))
            )
            confirm_button.click()
            time.sleep(3)
            print(f"下架完成，回到准备状态")
        except Exception as e:
            print(f'下架 {moment_id} 出现异常,错误为{e}')
        finally:
            # TODO Message: invalid session id
            self.driver.close()
            time.sleep(1)
            self.switch_to_tab(0)
            self.is_busy = False
            return

    def open_new_tab(self):
        self.driver.execute_script("window.open('');")
        tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(tab)

    def switch_to_tab(self, index):
        tab = self.driver.window_handles[index]
        self.driver.switch_to.window(tab)

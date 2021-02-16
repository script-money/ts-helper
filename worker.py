import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
import re
from enum import Enum
import logging
from exceptions import RegionNotAvaliableException

logger = logging.getLogger(__name__)

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
        self.headless = False
        capa = DesiredCapabilities.CHROME
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument(
                '--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.50"')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument("--window-size=1280, 800")  
        capa["pageLoadStrategy"] = "eager"
        self.driver = webdriver.Chrome(
            desired_capabilities=capa, chrome_options=chrome_options)
        self.wait = WebDriverWait(self.driver, 60)
    def launch(self):
        logger.info(f"headless mode: {self.headless}")
        self.is_busy = True
        # 登陆到dapper
        try:
            self.driver.get("https://www.nbatopshot.com/marketplace")
            if self.driver.title == "Not available in your region":
                logger.warning("请切换美国代理")
                raise RegionNotAvaliableException("Not available in your region")

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
            logger.info('登陆账号成功')
        except Exception as e:
            logger.error(f"登陆时出错，错误为{e}")
            self.driver.save_screenshot('error_screenshot.png')
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
            logger.warning(f'无法解析信号:{signal}')

    def buy(self, set_ID, play_ID, serial_number):
        if not (set_ID or play_ID or serial_number):
            logger.warning('请输入set_ID/play_ID/serial_number')
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
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(),'Pay with credit card')]"))
            )
            self.driver.find_element_by_xpath("//button[@type='button']").click()
            self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//span[@class='Label-sc-1c0wex9-0 bpIweo']"))
            )
            logger.info(
                f'购买 {set_ID}+{play_ID}?serialNumber={serial_number} 成功')
        except Exception as e:
            logger.warning(
                f'购买 {set_ID}+{play_ID}?serialNumber={serial_number} 失败, 错误是{e}')
        finally:
            self.driver.close()
            self.switch_to_tab(0)
            self.is_busy = False
            return

    def list_moment(self, moment_id, targetPrice):
        if not (moment_id or targetPrice):
            logger.warning('请输入moment_id/targetPrice')
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
            logger.info(f"上架完成，回到准备状态")
        except Exception as e:
            logger.warn(f'上架 {moment_id} 出现异常: {e}')
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
            logger.warning('请输入下架的moment_id')
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
            logger.info(f"下架完成，回到准备状态")
        except Exception as e:
            logger.warning(f'下架 {moment_id} 出现异常,错误为{e}')
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

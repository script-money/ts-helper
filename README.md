# nba_helper

## require

只拉数据不需要其他依赖

* python 3.8 (`sudo apt install python-is-python3`)

1. sudo apt-get update -y
2. sudo apt install gdebi-core wget unzip python3-pip python-is-python3 -y 
3. pip install -r requirements.txt

如果要运行web自动化脚本

* redis(suggest use `docker run -d -p 6379:6379 --name redis redis`)
* chrome and webdriver
* docker (https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)
  
1. wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
2. sudo gdebi google-chrome-stable_current_amd64.deb
3. wget https://chromedriver.storage.googleapis.com/88.0.4324.96/chromedriver_linux64.zip # 需要google-chrome --version 检查版本，webdriver版本和浏览器一致
4. unzip chromedriver_linux64.zip
5. sudo mv chromedriver /usr/bin/chromedriver
6. sudo chown root:root /usr/bin/chromedriver
7. sudo chmod +x /usr/bin/chromedriver

## run

1. modify *.env.example* to *.env* , then add your dappper email & password to *.env* file
2. `python run.py` launch selenium thread
3. modify SETID PLAYIDS TARGET_PRICE in *send_buy_signal*, use `python send_buy_signal.py` snipe low price and buy
# nba_helper

## require

* python 3.8
* redis(suggest use `docker run -d -p 6379:6379 --name redis redis`)
* chrome and webdriver

how to install chrome on ubuntu 20.10
> [安装 docker 参考](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-20-04)

1. sudo apt-get update -y
2. sudo apt install gdebi-core wget unzip python3-pip python-is-python3 -y
3. wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
4. sudo gdebi google-chrome-stable_current_amd64.deb
5. wget https://chromedriver.storage.googleapis.com/88.0.4324.96/chromedriver_linux64.zip # 需要google-chrome --version 检查版本，webdriver版本和浏览器一致
6. unzip chromedriver_linux64.zip
7. sudo mv chromedriver /usr/bin/chromedriver
8. sudo chown root:root /usr/bin/chromedriver
9. sudo chmod +x /usr/bin/chromedriver


## install

use `pip install -r requirements.txt` to install.

## run

1. modify *.env.example* to *.env* , then add your dappper email & password to *.env* file
2. `python run.py` launch selenium thread
3. modify SETID PLAYIDS TARGET_PRICE in *send_buy_signal*, use `python send_buy_signal.py` snipe low price and buy
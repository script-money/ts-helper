# nba_helper

## require

* python 3.8
* redis(suggest use `docker run -p 6379:6379 --name redis redis`)
* chrome and webdriver

## install

use `pip install -r requirements.txt` to install.

## run

1. modify *.env.example* to *.env* , then add your dappper email & password to *.env* file
2. `python run.py` launch selenium thread
3. modify SETID PLAYIDS TARGET_PRICE in *send_buy_signal*, use `python send_buy_signal.py` snipe low price and buy
from worker import Worker
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv('.env')
    account = os.getenv('DAPPER_ACCOUNT')
    password = os.getenv('DAPPER_PASSWORD')
    if account is None and password is None:
        print('请在.env中填入账号密码')
    worker = Worker(name='login',
                    account=account,
                    password=password)
    worker.launch()

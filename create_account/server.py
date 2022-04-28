import asyncio
import json
import os
import random
from create_account.logger import Logger

from web3 import Web3
from web3.middleware import geth_poa_middleware
import mongoengine
from create_account.database.keys import Keys
from eth_utils.currency import MAX_WEI, MIN_WEI

ROOT_PATH = os.path.split(os.path.realpath(__file__))[0]


class Server:

    def __init__(self, config, debug=False) -> None:
        self.config = config
        self.logger = Logger("create", debug=debug)
        self.provider = Web3.HTTPProvider(self.config['chain_rpc'])
        self.provider.middlewares.clear()
        self.web3 = Web3(self.provider)
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.db_data = mongoengine.connect(db=self.config['mongo']['db'], host=self.config['mongo']['host'])
        self.defaultAccount = self.config['main_account']

    def _get_abi(self, name: str):
        abi = []
        with open(f"{ROOT_PATH}/abis/{name}.json") as file:
            abi = json.load(file)
        return abi

    def multi_send(self, token, addresses, amounts, symbol):
        contract = self.web3.eth.contract(address=self.config['contracts']['MultiSend'], abi=self._get_abi("MultiSend"))
        value = 0
        for item in amounts:
            value += item
        self.logger.debug(f"Total token: {Web3.fromWei(value,'ether')} {symbol}")
        if token:
            tx = contract.functions.multi_send_token(token, addresses, amounts).buildTransaction({
                "from": self.defaultAccount,
                "gasPrice": self.web3.eth.gas_price
            })
        else:
            tx = contract.functions.multi_send_token("0x0000000000000000000000000000000000000000", addresses, amounts).buildTransaction({
                "from": self.defaultAccount,
                "gasPrice": self.web3.eth.gas_price,
                "value": value
            })
        # gas = self.web3.eth.estimateGas(tx)
        nonce = self.web3.eth.get_transaction_count(self.defaultAccount)
        # tx.update({'gas': gas})
        tx.update({'nonce': nonce})
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.config['main_account_key'])
        trx_id = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = self.web3.toHex(trx_id)
        result = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if result and result['status']:
            self.logger.debug(f"multi_send: hash={tx_hash}")
        else:
            self.logger.error(f"multi_send error: {tx_hash}")
            raise "multi_send error"

    def approve(self, address, amount, target_contract):
        contract = self.web3.eth.contract(address=address, abi=self._get_abi("ERC20"))
        tx = contract.functions.approve(target_contract, amount).buildTransaction({"from": self.defaultAccount, "gasPrice": self.web3.eth.gas_price})
        nonce = self.web3.eth.get_transaction_count(self.defaultAccount)
        tx.update({'nonce': nonce})
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.config['main_account_key'])
        trx_id = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = self.web3.toHex(trx_id)
        result = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if result and result['status']:
            self.logger.debug(f"approve: hash={tx_hash}")
        else:
            self.logger.error(f"approve error: {tx_hash}")
            raise "approve error"

    async def _run_transfer(self):
        """根据配置为所有地址分发代币"""
        accounts = Keys.objects(isTransfer=0).limit(self.config['account_count'])
        self.logger.debug(f"Read to {len(accounts)} addresses.")
        coins = self.config['distribute']
        addresses = []
        amounts = []
        coin_index = 1
        for coin in coins:
            token = coin['address']
            symbol = coin['symbol']
            self.logger.debug(f"distribute token [{symbol}]: {token}")
            if token:
                self.approve(token, MAX_WEI, self.config['contracts']['MultiSend'])
            random_range = coin['amount']
            max_amount = 0
            min_amount = 0
            if isinstance(random_range, list) and len(random_range) == 2:
                max_amount = int(Web3.toWei(random_range[1], "ether"))
                min_amount = int(Web3.toWei(random_range[0], "ether"))
            else:
                max_amount = min_amount = int(Web3.toWei(random_range, "ether"))
            self.logger.debug(f"Random range: min {max_amount}, max {min_amount}")
            save_accounts = []
            for account in accounts:
                if min_amount != max_amount:
                    amount = random.randrange(min_amount, max_amount, int(Web3.toWei(0.5, "ether")))
                else:
                    amount = max_amount
                amounts.append(amount)
                addresses.append(account.address)
                save_accounts.append(account)
                if len(addresses) == self.config['per_request']:
                    self.multi_send(token, addresses, amounts, symbol)
                    for ac in save_accounts:
                        ac.isTransfer = coin_index
                        ac.save()
                    self.logger.debug(f"Successfully distributed {len(addresses)} addresses")
                    save_accounts = []
                    addresses = []
                    amounts = []
            if len(addresses) > 0:
                self.multi_send(token, addresses, amounts, symbol)
                for ac in save_accounts:
                    ac.isTransfer = coin_index
                    ac.save()
                self.logger.debug(f"Successfully distributed {len(addresses)} addresses")
                save_accounts = []
                addresses = []
                amounts = []
            coin_index += 1
        # self.approve(token, MIN_WEI,self.config['contracts']['MultiSend'])

    def get_run_transfer_tasks(self, loop: asyncio.AbstractEventLoop):
        return [loop.create_task(self._run_transfer())]

    def _get_staking_address(self):
        coins = self.config['distribute']
        for coin in coins:
            if coin['symbol'] == self.config['staking_symbol']:
                return coin['address']
        return None

    async def _staking(self, account):
        address = self._get_staking_address()
        if not address:
            return
        erc20 = self.web3.eth.contract(address=address, abi=self._get_abi("ERC20"))
        contract = self.web3.eth.contract(address=self.config['contracts']['ERC20Staking'], abi=self._get_abi("ERC20Staking"))
        balance = erc20.functions.balanceOf(account.address).call()
        self.logger.debug(f"balance: {account.address} {Web3.fromWei(balance,'ether')} {self.config['staking_symbol']}")
        self.logger.debug(f"start approve: {account.address}")
        self.approve(erc20.address, balance, contract.address)
        await asyncio.sleep(3)
        self.logger.debug(f"start staking: {account.address} {Web3.fromWei(balance,'ether')} {self.config['staking_symbol']}")
        tx = contract.functions.deposit(balance).buildTransaction({"from": account.address, "gasPrice": self.web3.eth.gas_price})
        nonce = self.web3.eth.get_transaction_count(account.address)
        tx.update({'nonce': nonce})
        signed_tx = self.web3.eth.account.sign_transaction(tx, account.privateKey)
        trx_id = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hash = self.web3.toHex(trx_id)
        result = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if result and result['status']:
            self.logger.debug(f"staking: hash={tx_hash}")
            account.isMortgage = True
            account.save()
        else:
            self.logger.error(f"staking error: {tx_hash}")
            raise "staking error"

    async def _run_staking(self):
        """根据配置质押"""
        staking_interval = self.config['staking_interval']
        while True:
            try:
                account = Keys.objects(isTransfer=2, isMortgage=False).first()
                if account:
                    await self._staking(account)
                else:
                    self.logger.debug("staking complete.")
                    break
                await asyncio.sleep(staking_interval)
            except Exception as e:
                self.logger.exception(f"staking error: {e}")

    def get_run_staking_tasks(self, loop: asyncio.AbstractEventLoop):
        return [loop.create_task(self._run_staking())]

    def generate_address(self):
        """生成配置文件'account_count'中指定的数量地址"""
        count = self.config['account_count']
        self.logger.debug(f"Start generating addresses: {count} ...")
        try:
            i = 0
            for i in range(count):
                new_account = self.web3.eth.account.create(extra_entropy=f"nutbox bot account {i}")
                keys = Keys()
                keys.address = new_account.address
                keys.privateKey = new_account.privateKey.hex()
                keys.save()
            self.logger.debug(f"Total of {i+1} addresses were generated.")
        except Exception as e:
            self.logger.exception(f"generate address error: {e}")

    def drop_data(self):
        """从数据库中删除所有已经生成的数据"""
        count = Keys.objects.count()
        self.db_data.drop_database(self.config['mongo']['db'])
        self.logger.debug(f"Successfully cleaned {count} addresses.")

    def export_data(self, path: str):
        """导出数据到指定'path'文件中"""
        data = Keys.objects().to_json()
        with open(path, "w") as file:
            file.write(data)

    def run_transfer(self):
        """根据配置为所有地址分发代币"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(self.get_run_transfer_tasks(loop)))
        loop.close()

    def run_staking(self):
        """根据配置质押"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(self.get_run_staking_tasks(loop)))
        loop.close()
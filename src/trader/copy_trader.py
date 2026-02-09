"""
Copy Trader - Automatically copy trades from tracked wallets
"""

import asyncio
from web3 import Web3
from typing import Dict, Optional
from colorama import Fore, Style


class CopyTrader:
    def __init__(self, config: dict, wallets_config: dict, alerts):
        self.config = config
        self.wallets_config = wallets_config
        self.alerts = alerts
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.running = False
        
        # Account setup
        self.private_key = config['wallet']['private_key']
        self.address = config['wallet']['address']
        
        # Copy trade settings
        self.enabled = config['copy_trade']['enabled']
        self.max_amount = config['copy_trade']['max_copy_amount_eth']
        self.delay = config['copy_trade']['copy_delay_seconds']
        
        # Wallets to copy
        self.copy_wallets = {
            w['address'].lower(): w 
            for w in wallets_config['tracked_wallets'] 
            if w.get('copy_trade', False)
        }
        
        # Pending copies
        self.pending_copies = []
        self.executed_copies = set()
        
    async def start(self):
        self.running = True
        copy_count = len(self.copy_wallets)
        print(f"{Fore.GREEN}[CopyTrader] Started - Copying {copy_count} wallets...{Style.RESET_ALL}")
        print(f"{Fore.WHITE}[CopyTrader] Max copy: {self.max_amount} ETH | Delay: {self.delay}s{Style.RESET_ALL}")
        
        while self.running:
            try:
                if self.pending_copies:
                    trade = self.pending_copies.pop(0)
                    await self.execute_copy(trade)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[CopyTrader] Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    def queue_copy(self, trade_data: Dict):
        """Add a trade to the copy queue"""
        tx_hash = trade_data['tx'].hash.hex()
        
        if tx_hash in self.executed_copies:
            return
        
        wallet = trade_data['wallet']
        if wallet['address'].lower() not in self.copy_wallets:
            return
        
        if trade_data['type'] not in ['BUY', 'SELL']:
            return
        
        self.pending_copies.append(trade_data)
        print(f"{Fore.CYAN}[CopyTrader] Queued copy: {trade_data['type']} from {wallet['label']}{Style.RESET_ALL}")
    
    async def execute_copy(self, trade_data: Dict):
        """Execute a copy trade"""
        tx_hash = trade_data['tx'].hash.hex()
        
        if tx_hash in self.executed_copies:
            return
        
        self.executed_copies.add(tx_hash)
        
        # Apply delay
        if self.delay > 0:
            print(f"{Fore.WHITE}[CopyTrader] Waiting {self.delay}s before copy...{Style.RESET_ALL}")
            await asyncio.sleep(self.delay)
        
        try:
            original_tx = trade_data['tx']
            wallet_label = trade_data['wallet']['label']
            trade_type = trade_data['type']
            
            if trade_type == 'BUY':
                # Copy the buy
                # Scale down to max_amount if original is larger
                original_value = self.w3.from_wei(original_tx.value, 'ether')
                copy_value = min(float(original_value), self.max_amount)
                
                result = await self.copy_buy(original_tx, copy_value)
            
            elif trade_type == 'SELL':
                # Copy the sell (sell same token)
                result = await self.copy_sell(original_tx)
            
            if result:
                message = f"""
📋 **COPY TRADE EXECUTED**

👤 Copied: {wallet_label}
📊 Action: {trade_type}
💰 Amount: {self.max_amount} ETH

🔗 [TX]({self.config['network']['explorer_url']}/tx/{result})
"""
                print(f"{Fore.GREEN}[CopyTrader] ✓ Copied {trade_type} from {wallet_label}{Style.RESET_ALL}")
                await self.alerts.send(message)
            
        except Exception as e:
            print(f"{Fore.RED}[CopyTrader] Copy failed: {e}{Style.RESET_ALL}")
    
    async def copy_buy(self, original_tx, amount_eth: float) -> Optional[str]:
        """Copy a buy transaction"""
        if self.private_key == "YOUR_PRIVATE_KEY_HERE":
            print(f"{Fore.RED}[CopyTrader] ERROR: Private key not configured!{Style.RESET_ALL}")
            return None
        
        try:
            # Replicate the transaction with our parameters
            tx = {
                'to': original_tx.to,
                'from': self.address,
                'value': self.w3.to_wei(amount_eth, 'ether'),
                'data': original_tx.input,
                'gas': original_tx.gas,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address)
            }
            
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                return tx_hash.hex()
            return None
            
        except Exception as e:
            print(f"{Fore.RED}[CopyTrader] Buy copy error: {e}{Style.RESET_ALL}")
            return None
    
    async def copy_sell(self, original_tx) -> Optional[str]:
        """Copy a sell transaction"""
        # Implementation similar to copy_buy
        # Need to decode the original tx to get token address and amounts
        pass
    
    def add_wallet_to_copy(self, address: str, label: str):
        """Add a wallet to copy trading"""
        self.copy_wallets[address.lower()] = {
            'address': address,
            'label': label,
            'copy_trade': True
        }
        print(f"{Fore.GREEN}[CopyTrader] Added wallet to copy: {label}{Style.RESET_ALL}")
    
    def stop(self):
        self.running = False
        print(f"{Fore.RED}[CopyTrader] Stopped{Style.RESET_ALL}")

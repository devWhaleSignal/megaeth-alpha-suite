"""
Wallet Tracker - Monitor whale wallets and their transactions
"""

import asyncio
from web3 import Web3
from typing import List, Dict
from colorama import Fore, Style


class WalletTracker:
    def __init__(self, config: dict, wallets_config: dict, alerts):
        self.config = config
        self.wallets_config = wallets_config
        self.alerts = alerts
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.running = False
        self.tracked_wallets = {
            w['address'].lower(): w for w in wallets_config['tracked_wallets']
        }
        self.last_tx_hashes = {}
        
    async def start(self):
        self.running = True
        wallet_count = len(self.tracked_wallets)
        print(f"{Fore.GREEN}[Tracker] Started - Monitoring {wallet_count} wallets...{Style.RESET_ALL}")
        
        last_block = self.w3.eth.block_number
        
        while self.running:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    for block_num in range(last_block + 1, current_block + 1):
                        await self.scan_block_for_wallets(block_num)
                    last_block = current_block
                
                await asyncio.sleep(0.5)
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[Tracker] Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    async def scan_block_for_wallets(self, block_number: int):
        """Scan block for transactions from tracked wallets"""
        try:
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            
            for tx in block.transactions:
                sender = tx['from'].lower() if tx.get('from') else None
                
                if sender and sender in self.tracked_wallets:
                    await self.process_wallet_tx(tx, self.tracked_wallets[sender])
                    
        except Exception as e:
            print(f"{Fore.RED}[Tracker] Block scan error: {e}{Style.RESET_ALL}")
    
    async def process_wallet_tx(self, tx, wallet_info: Dict):
        """Process a transaction from a tracked wallet"""
        tx_hash = tx.hash.hex()
        
        # Skip if already processed
        if tx_hash in self.last_tx_hashes.get(wallet_info['address'], set()):
            return
            
        if wallet_info['address'] not in self.last_tx_hashes:
            self.last_tx_hashes[wallet_info['address']] = set()
        self.last_tx_hashes[wallet_info['address']].add(tx_hash)
        
        # Decode transaction
        tx_type, details = await self.decode_transaction(tx)
        
        # Build alert
        message = f"""
🐋 **WHALE ACTIVITY**

👤 Wallet: {wallet_info['label']}
📍 Address: `{wallet_info['address'][:10]}...{wallet_info['address'][-8:]}`

📊 Action: {tx_type}
{details}

🔗 [TX]({self.config['network']['explorer_url']}/tx/{tx_hash})
"""
        
        print(f"{Fore.MAGENTA}[Tracker] {wallet_info['label']}: {tx_type}{Style.RESET_ALL}")
        
        if wallet_info.get('alert_on_trade'):
            await self.alerts.send(message)
        
        # Return for copy trading
        return {
            'wallet': wallet_info,
            'tx': tx,
            'type': tx_type,
            'details': details
        }
    
    async def decode_transaction(self, tx) -> tuple:
        """Decode transaction to determine type and details"""
        # Common DEX router methods
        SWAP_METHODS = {
            '0x7ff36ab5': 'swapExactETHForTokens',
            '0x38ed1739': 'swapExactTokensForTokens',
            '0x18cbafe5': 'swapExactTokensForETH',
            '0xfb3bdb41': 'swapETHForExactTokens',
            '0x5c11d795': 'swapExactTokensForTokensSupportingFeeOnTransferTokens',
            '0x791ac947': 'swapExactTokensForETHSupportingFeeOnTransferTokens',
            '0xb6f9de95': 'swapExactETHForTokensSupportingFeeOnTransferTokens',
        }
        
        input_data = tx.input.hex() if tx.input else ''
        method_id = input_data[:10] if len(input_data) >= 10 else ''
        
        if method_id in SWAP_METHODS:
            method_name = SWAP_METHODS[method_id]
            value_eth = self.w3.from_wei(tx.value, 'ether')
            
            if 'ETHFor' in method_name:
                return "BUY", f"💰 Amount: {value_eth:.4f} ETH"
            elif 'ForETH' in method_name:
                return "SELL", f"💰 Received: ~{value_eth:.4f} ETH"
            else:
                return "SWAP", f"🔄 Token to Token swap"
        
        elif tx.value > 0:
            value_eth = self.w3.from_wei(tx.value, 'ether')
            return "TRANSFER", f"💸 Amount: {value_eth:.4f} ETH"
        
        else:
            return "CONTRACT INTERACTION", f"📝 To: {tx.to[:10]}..."
    
    def add_wallet(self, address: str, label: str, copy_trade: bool = False):
        """Add a wallet to track"""
        self.tracked_wallets[address.lower()] = {
            'address': address,
            'label': label,
            'copy_trade': copy_trade,
            'alert_on_trade': True
        }
        print(f"{Fore.GREEN}[Tracker] Added wallet: {label}{Style.RESET_ALL}")
    
    def remove_wallet(self, address: str):
        """Remove a wallet from tracking"""
        if address.lower() in self.tracked_wallets:
            del self.tracked_wallets[address.lower()]
            print(f"{Fore.YELLOW}[Tracker] Removed wallet: {address}{Style.RESET_ALL}")
    
    def stop(self):
        self.running = False
        print(f"{Fore.RED}[Tracker] Stopped{Style.RESET_ALL}")

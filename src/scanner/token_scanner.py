"""
Token Scanner - Detects new token deployments on MegaETH
"""

import asyncio
from web3 import Web3
from typing import Optional
from colorama import Fore, Style


class TokenScanner:
    def __init__(self, config: dict, analyzer, alerts):
        self.config = config
        self.analyzer = analyzer
        self.alerts = alerts
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.scanned_tokens = set()
        self.running = False
        
        # ERC20 creation signature (Transfer from 0x0)
        self.TRANSFER_TOPIC = self.w3.keccak(text="Transfer(address,address,uint256)").hex()
        self.ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
        
    async def start(self):
        self.running = True
        print(f"{Fore.GREEN}[Scanner] Started - Monitoring for new tokens...{Style.RESET_ALL}")
        
        last_block = self.w3.eth.block_number
        
        while self.running:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_block:
                    for block_num in range(last_block + 1, current_block + 1):
                        await self.scan_block(block_num)
                    last_block = current_block
                
                await asyncio.sleep(self.config['scanner']['scan_interval_seconds'])
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[Scanner] Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    async def scan_block(self, block_number: int):
        """Scan a block for new token creations"""
        try:
            block = self.w3.eth.get_block(block_number, full_transactions=True)
            
            for tx in block.transactions:
                # Check for contract creation (to = None)
                if tx.to is None:
                    receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                    if receipt.contractAddress:
                        await self.analyze_new_contract(receipt.contractAddress, tx)
                        
        except Exception as e:
            print(f"{Fore.RED}[Scanner] Block scan error: {e}{Style.RESET_ALL}")
    
    async def analyze_new_contract(self, contract_address: str, tx):
        """Analyze a newly deployed contract"""
        if contract_address in self.scanned_tokens:
            return
            
        self.scanned_tokens.add(contract_address)
        
        # Check if it's an ERC20
        is_token = await self.analyzer.is_erc20(contract_address)
        if not is_token:
            return
        
        # Get token info
        token_info = await self.analyzer.get_token_info(contract_address)
        if not token_info:
            return
        
        # Security analysis
        security = await self.analyzer.analyze_security(contract_address)
        
        # Check liquidity
        liquidity = await self.analyzer.get_liquidity(contract_address)
        
        if liquidity < self.config['scanner']['min_liquidity_usd']:
            return
        
        # Build alert message
        risk_emoji = "🟢" if security['safe'] else "🔴"
        
        message = f"""
🆕 **NEW TOKEN DETECTED**

📝 Name: {token_info['name']}
🔤 Symbol: {token_info['symbol']}
📍 Address: `{contract_address}`

💰 Liquidity: ${liquidity:,.2f}
{risk_emoji} Security: {'SAFE' if security['safe'] else 'RISKY'}

⚠️ Risks:
- Honeypot: {'Yes' if security.get('is_honeypot') else 'No'}
- Buy Tax: {security.get('buy_tax', 'Unknown')}%
- Sell Tax: {security.get('sell_tax', 'Unknown')}%

🔗 [Explorer]({self.config['network']['explorer_url']}/token/{contract_address})
"""
        
        print(f"{Fore.YELLOW}[Scanner] New token: {token_info['symbol']} at {contract_address}{Style.RESET_ALL}")
        await self.alerts.send(message)
        
        return {
            'address': contract_address,
            'info': token_info,
            'security': security,
            'liquidity': liquidity
        }
    
    def stop(self):
        self.running = False
        print(f"{Fore.RED}[Scanner] Stopped{Style.RESET_ALL}")

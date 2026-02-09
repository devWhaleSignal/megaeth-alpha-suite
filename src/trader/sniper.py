"""
Sniper Bot - Auto-buy new tokens that pass security checks
"""

import asyncio
from web3 import Web3
from typing import Dict, Optional
from colorama import Fore, Style


# Uniswap V2 Router ABI (simplified)
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokensSupportingFeeOnTransferTokens",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETHSupportingFeeOnTransferTokens",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class Sniper:
    def __init__(self, config: dict, analyzer, alerts):
        self.config = config
        self.analyzer = analyzer
        self.alerts = alerts
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.running = False
        
        # Setup account
        self.private_key = config['wallet']['private_key']
        self.address = config['wallet']['address']
        
        # Trading params
        self.max_buy = config['trading']['max_buy_amount_eth']
        self.slippage = config['trading']['slippage_percent']
        self.gas_limit = config['trading']['gas_limit']
        
        # Pending snipes
        self.pending_snipes = []
        self.sniped_tokens = set()
        
    async def start(self):
        self.running = True
        print(f"{Fore.GREEN}[Sniper] Started - Ready to snipe...{Style.RESET_ALL}")
        print(f"{Fore.WHITE}[Sniper] Max buy: {self.max_buy} ETH | Slippage: {self.slippage}%{Style.RESET_ALL}")
        
        while self.running:
            try:
                # Process pending snipes
                if self.pending_snipes:
                    token = self.pending_snipes.pop(0)
                    await self.snipe_token(token)
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[Sniper] Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    def add_to_snipe_queue(self, token_data: Dict):
        """Add a token to the snipe queue"""
        if token_data['address'] not in self.sniped_tokens:
            self.pending_snipes.append(token_data)
            print(f"{Fore.YELLOW}[Sniper] Added to queue: {token_data.get('symbol', 'Unknown')}{Style.RESET_ALL}")
    
    async def snipe_token(self, token_data: Dict):
        """Execute a snipe on a token"""
        token_address = token_data['address']
        
        if token_address in self.sniped_tokens:
            return
        
        # Final security check
        security = await self.analyzer.analyze_security(token_address)
        if not security['safe']:
            print(f"{Fore.RED}[Sniper] Skipping {token_address} - Failed security check{Style.RESET_ALL}")
            return
        
        self.sniped_tokens.add(token_address)
        
        try:
            # Execute buy
            tx_hash = await self.buy_token(token_address, self.max_buy)
            
            if tx_hash:
                message = f"""
🎯 **SNIPE EXECUTED**

🪙 Token: {token_data.get('symbol', 'Unknown')}
📍 Address: `{token_address}`
💰 Amount: {self.max_buy} ETH

🔗 [TX]({self.config['network']['explorer_url']}/tx/{tx_hash})
"""
                print(f"{Fore.GREEN}[Sniper] ✓ Sniped {token_data.get('symbol', 'Unknown')}{Style.RESET_ALL}")
                await self.alerts.send(message)
            
        except Exception as e:
            print(f"{Fore.RED}[Sniper] Snipe failed: {e}{Style.RESET_ALL}")
    
    async def buy_token(self, token_address: str, amount_eth: float) -> Optional[str]:
        """Buy a token with ETH"""
        if self.private_key == "YOUR_PRIVATE_KEY_HERE":
            print(f"{Fore.RED}[Sniper] ERROR: Private key not configured!{Style.RESET_ALL}")
            return None
        
        try:
            # Get router address (will need to be updated for MegaETH DEXes)
            router_address = "0x0000000000000000000000000000000000000000"  # Placeholder
            
            router = self.w3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=ROUTER_ABI
            )
            
            # WETH address (will need to be updated for MegaETH)
            weth_address = "0x0000000000000000000000000000000000000000"  # Placeholder
            
            # Build path
            path = [weth_address, Web3.to_checksum_address(token_address)]
            
            # Calculate deadline
            deadline = self.w3.eth.get_block('latest').timestamp + 300
            
            # Build transaction
            tx = router.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
                0,  # amountOutMin (0 for max slippage)
                path,
                Web3.to_checksum_address(self.address),
                deadline
            ).build_transaction({
                'from': self.address,
                'value': self.w3.to_wei(amount_eth, 'ether'),
                'gas': self.gas_limit,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.address)
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            if receipt.status == 1:
                return tx_hash.hex()
            else:
                print(f"{Fore.RED}[Sniper] Transaction failed{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            print(f"{Fore.RED}[Sniper] Buy error: {e}{Style.RESET_ALL}")
            return None
    
    async def sell_token(self, token_address: str, percentage: int = 100) -> Optional[str]:
        """Sell a token for ETH"""
        # Similar to buy but reversed
        # Implementation placeholder
        pass
    
    def stop(self):
        self.running = False
        print(f"{Fore.RED}[Sniper] Stopped{Style.RESET_ALL}")

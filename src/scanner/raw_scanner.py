"""
Raw Token Scanner - Detects ALL token deployments, with or without liquidity
"""

import asyncio
import time
from web3 import Web3
from typing import Dict, List, Optional
from datetime import datetime


class RawTokenScanner:
    def __init__(self, config: dict):
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.config = config
        self.last_scanned_block = None
        self.known_tokens: set = set()
        
        # ERC20 signatures
        self.TRANSFER_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        self.APPROVAL_SIGNATURE = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
        
        # Common ERC20 bytecode patterns
        self.ERC20_PATTERNS = [
            b'totalSupply',
            b'balanceOf',
            b'transfer',
            b'allowance',
            b'approve',
            b'transferFrom'
        ]
    
    async def scan_new_deployments(self) -> List[Dict]:
        """Scan for new contract deployments"""
        if not self.w3.is_connected():
            print("❌ Not connected to RPC")
            return []
        
        try:
            current_block = self.w3.eth.block_number
            
            if self.last_scanned_block is None:
                # Start from recent blocks
                self.last_scanned_block = current_block - 100
            
            new_tokens = []
            
            # Scan blocks since last check
            for block_num in range(self.last_scanned_block + 1, current_block + 1):
                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        # Check if it's a contract deployment (to == None)
                        if tx['to'] is None:
                            receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
                            contract_address = receipt['contractAddress']
                            
                            if contract_address and contract_address not in self.known_tokens:
                                # Check if it's an ERC20
                                if await self.is_erc20(contract_address):
                                    token_info = await self.get_token_info(contract_address, tx, block)
                                    if token_info:
                                        new_tokens.append(token_info)
                                        self.known_tokens.add(contract_address)
                                        print(f"🆕 New token: {token_info['name']} ({token_info['symbol']}) at {contract_address}")
                
                except Exception as e:
                    print(f"Error scanning block {block_num}: {e}")
                    continue
            
            self.last_scanned_block = current_block
            return new_tokens
            
        except Exception as e:
            print(f"Error in scan_new_deployments: {e}")
            return []
    
    async def is_erc20(self, address: str) -> bool:
        """Check if contract is an ERC20 token"""
        try:
            code = self.w3.eth.get_code(address)
            
            if len(code) < 100:
                return False
            
            # Check for ERC20 function signatures in bytecode
            code_bytes = bytes(code)
            matches = sum(1 for pattern in self.ERC20_PATTERNS if pattern in code_bytes)
            
            if matches >= 4:  # At least 4 ERC20 functions
                return True
            
            # Try calling ERC20 methods
            abi = [
                {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'}
            ]
            contract = self.w3.eth.contract(address=address, abi=abi)
            
            try:
                contract.functions.totalSupply().call()
                contract.functions.decimals().call()
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            return False
    
    async def get_token_info(self, address: str, tx: dict, block: dict) -> Optional[Dict]:
        """Get token information"""
        try:
            abi = [
                {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'},
                {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'type': 'function'}
            ]
            
            contract = self.w3.eth.contract(address=address, abi=abi)
            
            try:
                name = contract.functions.name().call()
            except:
                name = "Unknown"
            
            try:
                symbol = contract.functions.symbol().call()
            except:
                symbol = "???"
            
            try:
                decimals = contract.functions.decimals().call()
            except:
                decimals = 18
            
            try:
                total_supply = contract.functions.totalSupply().call()
            except:
                total_supply = 0
            
            try:
                owner = contract.functions.owner().call()
            except:
                owner = None
            
            deployer = tx['from']
            
            return {
                'address': address,
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'total_supply': total_supply,
                'deployer': deployer,
                'owner': owner,
                'block_number': block['number'],
                'timestamp': datetime.fromtimestamp(block['timestamp']).isoformat(),
                'tx_hash': tx['hash'].hex(),
                'has_liquidity': False,  # We'll check this separately
                'liquidity_usd': 0,
                'verified': False,
                'confidence_score': 30  # Low score for tokens without liquidity
            }
            
        except Exception as e:
            print(f"Error getting token info for {address}: {e}")
            return None
    
    async def run(self):
        """Main scanning loop"""
        print("🔍 Raw Token Scanner started")
        print(f"Connected to chain ID: {self.w3.eth.chain_id}")
        
        while True:
            try:
                new_tokens = await self.scan_new_deployments()
                
                if new_tokens:
                    print(f"✅ Found {len(new_tokens)} new tokens")
                    # Here you can send to dashboard, save to DB, etc.
                
                await asyncio.sleep(self.config['scanner']['scan_interval_seconds'])
                
            except KeyboardInterrupt:
                print("\n⏹️  Scanner stopped")
                break
            except Exception as e:
                print(f"Error in scanner loop: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    import json
    with open('config/settings.json') as f:
        config = json.load(f)
    
    scanner = RawTokenScanner(config)
    asyncio.run(scanner.run())

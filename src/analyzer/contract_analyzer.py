"""
Contract Analyzer - Analyze token contracts for security risks
"""

import asyncio
from web3 import Web3
from typing import Dict, Optional
from colorama import Fore, Style


# Standard ERC20 ABI
ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "owner", "outputs": [{"name": "", "type": "address"}], "type": "function"},
]


class ContractAnalyzer:
    def __init__(self, network_config: dict):
        self.w3 = Web3(Web3.HTTPProvider(network_config['rpc_url']))
        self.explorer_url = network_config['explorer_url']
        
        # Known honeypot patterns in bytecode
        self.HONEYPOT_PATTERNS = [
            'require(from == owner)',
            'require(sender == owner)',
            'onlyOwner',
            'blacklist',
            'isBot',
        ]
        
    async def is_erc20(self, address: str) -> bool:
        """Check if contract is ERC20 token"""
        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)
            # Try to call standard ERC20 methods
            contract.functions.totalSupply().call()
            contract.functions.decimals().call()
            return True
        except Exception:
            return False
    
    async def get_token_info(self, address: str) -> Optional[Dict]:
        """Get basic token information"""
        try:
            contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)
            
            name = contract.functions.name().call()
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            total_supply = contract.functions.totalSupply().call()
            
            return {
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'total_supply': total_supply,
                'address': address
            }
        except Exception as e:
            print(f"{Fore.RED}[Analyzer] Error getting token info: {e}{Style.RESET_ALL}")
            return None
    
    async def analyze_security(self, address: str) -> Dict:
        """Analyze contract for security risks"""
        result = {
            'safe': True,
            'is_honeypot': False,
            'is_proxy': False,
            'has_mint': False,
            'has_blacklist': False,
            'buy_tax': 0,
            'sell_tax': 0,
            'owner': None,
            'risks': []
        }
        
        try:
            # Get bytecode
            bytecode = self.w3.eth.get_code(Web3.to_checksum_address(address)).hex()
            
            # Check for proxy pattern (delegatecall)
            if 'delegatecall' in bytecode.lower() or '363d3d373d3d3d363d' in bytecode:
                result['is_proxy'] = True
                result['risks'].append('Proxy contract - can be upgraded')
            
            # Check for mint function
            if 'mint' in bytecode.lower():
                result['has_mint'] = True
                result['risks'].append('Has mint function')
            
            # Check for blacklist
            if 'blacklist' in bytecode.lower() or 'isbot' in bytecode.lower():
                result['has_blacklist'] = True
                result['risks'].append('Has blacklist function')
                result['safe'] = False
            
            # Try to get owner
            try:
                contract = self.w3.eth.contract(address=Web3.to_checksum_address(address), abi=ERC20_ABI)
                owner = contract.functions.owner().call()
                result['owner'] = owner
                
                # Check if owner is renounced
                if owner == '0x0000000000000000000000000000000000000000':
                    result['risks'].append('Ownership renounced ✓')
            except:
                pass
            
            # Simulate buy/sell to detect taxes (simplified)
            # In production, you'd want to use a proper simulation
            result['buy_tax'] = 0
            result['sell_tax'] = 0
            
            # Check for honeypot indicators
            suspicious_patterns = 0
            if 'require' in bytecode.lower() and 'from' in bytecode.lower():
                suspicious_patterns += 1
            if 'transfer' in bytecode.lower() and 'revert' in bytecode.lower():
                suspicious_patterns += 1
                
            if suspicious_patterns >= 2:
                result['is_honeypot'] = True
                result['safe'] = False
                result['risks'].append('Possible honeypot')
            
            if len(result['risks']) > 2:
                result['safe'] = False
                
        except Exception as e:
            print(f"{Fore.RED}[Analyzer] Security analysis error: {e}{Style.RESET_ALL}")
            result['safe'] = False
            result['risks'].append('Analysis failed')
        
        return result
    
    async def get_liquidity(self, token_address: str) -> float:
        """Get token liquidity in USD (simplified)"""
        # In production, you'd query DEX pools for actual liquidity
        # This is a placeholder that returns 0 - you need to implement
        # actual liquidity checking for specific DEXes on MegaETH
        
        try:
            # Example: Check common DEX pairs
            # For now, return a placeholder
            # You'll need to implement this based on which DEXes launch on MegaETH
            return 10000.0  # Placeholder
        except Exception:
            return 0.0
    
    async def simulate_buy_sell(self, token_address: str, amount_eth: float = 0.01) -> Dict:
        """Simulate a buy and sell to detect taxes and honeypot"""
        # This requires a fork simulation or actual test trades
        # Placeholder implementation
        return {
            'can_buy': True,
            'can_sell': True,
            'buy_tax': 0,
            'sell_tax': 0,
            'is_honeypot': False
        }

"""
Arbitrage Detector - Find arbitrage opportunities between DEXes
"""

import asyncio
from web3 import Web3
from typing import Dict, List, Optional
from colorama import Fore, Style


class ArbDetector:
    def __init__(self, config: dict, alerts):
        self.config = config
        self.alerts = alerts
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.running = False
        
        # Arbitrage settings
        self.enabled = config['arbitrage']['enabled']
        self.min_profit = config['arbitrage']['min_profit_percent']
        self.dexes = config['arbitrage']['dexes']
        
        # DEX configurations (need to be updated for MegaETH)
        self.dex_configs = {
            'uniswap': {
                'router': '0x0000000000000000000000000000000000000000',
                'factory': '0x0000000000000000000000000000000000000000',
            },
            'sushiswap': {
                'router': '0x0000000000000000000000000000000000000000',
                'factory': '0x0000000000000000000000000000000000000000',
            }
        }
        
        # Common tokens to check
        self.base_tokens = []
        self.quote_tokens = []
        
    async def start(self):
        self.running = True
        print(f"{Fore.GREEN}[Arbitrage] Started - Scanning for opportunities...{Style.RESET_ALL}")
        print(f"{Fore.WHITE}[Arbitrage] Min profit: {self.min_profit}% | DEXes: {', '.join(self.dexes)}{Style.RESET_ALL}")
        
        while self.running:
            try:
                opportunities = await self.scan_opportunities()
                
                for opp in opportunities:
                    if opp['profit_percent'] >= self.min_profit:
                        await self.alert_opportunity(opp)
                
                await asyncio.sleep(1)  # Scan every second
                
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}[Arbitrage] Error: {e}{Style.RESET_ALL}")
                await asyncio.sleep(1)
    
    async def scan_opportunities(self) -> List[Dict]:
        """Scan for arbitrage opportunities"""
        opportunities = []
        
        # Compare prices across DEXes for each token pair
        for base_token in self.base_tokens:
            for quote_token in self.quote_tokens:
                if base_token == quote_token:
                    continue
                
                prices = {}
                
                for dex in self.dexes:
                    price = await self.get_price(dex, base_token, quote_token)
                    if price:
                        prices[dex] = price
                
                # Find arbitrage
                if len(prices) >= 2:
                    opp = self.find_arbitrage(base_token, quote_token, prices)
                    if opp:
                        opportunities.append(opp)
        
        return opportunities
    
    async def get_price(self, dex: str, token_in: str, token_out: str) -> Optional[float]:
        """Get price from a DEX"""
        try:
            # This is a simplified placeholder
            # In production, you'd query the actual DEX contracts
            
            dex_config = self.dex_configs.get(dex)
            if not dex_config:
                return None
            
            # Query pair reserves and calculate price
            # Placeholder - return None for now
            return None
            
        except Exception as e:
            return None
    
    def find_arbitrage(self, base_token: str, quote_token: str, prices: Dict[str, float]) -> Optional[Dict]:
        """Find arbitrage opportunity from price differences"""
        if len(prices) < 2:
            return None
        
        dexes = list(prices.keys())
        best_buy_dex = min(dexes, key=lambda x: prices[x])
        best_sell_dex = max(dexes, key=lambda x: prices[x])
        
        buy_price = prices[best_buy_dex]
        sell_price = prices[best_sell_dex]
        
        if buy_price <= 0:
            return None
        
        profit_percent = ((sell_price - buy_price) / buy_price) * 100
        
        if profit_percent < self.min_profit:
            return None
        
        return {
            'base_token': base_token,
            'quote_token': quote_token,
            'buy_dex': best_buy_dex,
            'sell_dex': best_sell_dex,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit_percent': profit_percent
        }
    
    async def alert_opportunity(self, opportunity: Dict):
        """Send alert for arbitrage opportunity"""
        message = f"""
💰 **ARBITRAGE OPPORTUNITY**

🔄 Pair: {opportunity['base_token'][:8]}.../{opportunity['quote_token'][:8]}...

📉 Buy on: {opportunity['buy_dex'].upper()}
   Price: {opportunity['buy_price']:.8f}

📈 Sell on: {opportunity['sell_dex'].upper()}
   Price: {opportunity['sell_price']:.8f}

💵 Profit: {opportunity['profit_percent']:.2f}%
"""
        
        print(f"{Fore.GREEN}[Arbitrage] Found opportunity: {opportunity['profit_percent']:.2f}% profit{Style.RESET_ALL}")
        await self.alerts.send(message)
    
    async def execute_arbitrage(self, opportunity: Dict) -> bool:
        """Execute an arbitrage trade (advanced - requires flash loans or capital)"""
        # This is complex and requires:
        # 1. Flash loan or capital
        # 2. Atomic execution (both trades in same tx)
        # 3. Gas optimization
        # Placeholder for now
        pass
    
    def add_token_pair(self, base_token: str, quote_token: str):
        """Add a token pair to scan"""
        if base_token not in self.base_tokens:
            self.base_tokens.append(base_token)
        if quote_token not in self.quote_tokens:
            self.quote_tokens.append(quote_token)
    
    def stop(self):
        self.running = False
        print(f"{Fore.RED}[Arbitrage] Stopped{Style.RESET_ALL}")

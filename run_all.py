#!/usr/bin/env python3
"""
Run both the MegaETH Alpha Suite Bot and Web Dashboard
"""

import asyncio
import threading
import uvicorn
from web.server import app

# Import bot modules
from src.scanner.token_scanner import TokenScanner
from src.tracker.wallet_tracker import WalletTracker
from src.arbitrage.arb_detector import ArbDetector
from src.analyzer.contract_analyzer import ContractAnalyzer
from src.alerts.telegram_bot import TelegramAlert

import json
from pathlib import Path
import aiohttp

# Web API URL for pushing data to dashboard
WEB_API_URL = "http://localhost:8000/api"

class BotWithWebIntegration:
    def __init__(self):
        # Load config
        config_path = Path(__file__).parent / "config" / "settings.json"
        wallets_path = Path(__file__).parent / "config" / "wallets.json"
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        with open(wallets_path, 'r') as f:
            self.wallets_config = json.load(f)
        
        # Initialize modules
        self.alerts = TelegramAlert(self.config['alerts'])
        self.analyzer = ContractAnalyzer(self.config['network'])
        self.scanner = TokenScanner(self.config, self.analyzer, self.alerts)
        self.tracker = WalletTracker(self.config, self.wallets_config, self.alerts)
        self.arb_detector = ArbDetector(self.config, self.alerts)
        
    async def push_to_web(self, endpoint: str, data: dict):
        """Push data to web dashboard"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{WEB_API_URL}/{endpoint}", json=data) as resp:
                    pass
        except Exception as e:
            pass  # Web server might not be ready yet
    
    async def run_scanner_with_web(self):
        """Run scanner and push results to web"""
        # Override the scanner's analyze_new_contract to also push to web
        original_analyze = self.scanner.analyze_new_contract
        
        async def analyze_and_push(contract_address, tx):
            result = await original_analyze(contract_address, tx)
            if result:
                await self.push_to_web("token", result)
            return result
        
        self.scanner.analyze_new_contract = analyze_and_push
        await self.scanner.start()
    
    async def run_tracker_with_web(self):
        """Run tracker and push results to web"""
        original_process = self.tracker.process_wallet_tx
        
        async def process_and_push(tx, wallet_info):
            result = await original_process(tx, wallet_info)
            if result:
                web_data = {
                    'wallet': result['wallet'],
                    'type': result['type'],
                    'amount': str(self.tracker.w3.from_wei(tx.value, 'ether')) if tx.value else '0',
                    'tx_hash': tx.hash.hex(),
                    'token': 'Unknown'
                }
                await self.push_to_web("trade", web_data)
            return result
        
        self.tracker.process_wallet_tx = process_and_push
        await self.tracker.start()
    
    async def run_arb_with_web(self):
        """Run arbitrage detector and push results to web"""
        original_alert = self.arb_detector.alert_opportunity
        
        async def alert_and_push(opportunity):
            await original_alert(opportunity)
            await self.push_to_web("arb", opportunity)
        
        self.arb_detector.alert_opportunity = alert_and_push
        await self.arb_detector.start()
    
    async def run_all_bots(self):
        """Run all bots concurrently"""
        await asyncio.gather(
            self.run_scanner_with_web(),
            self.run_tracker_with_web(),
            self.run_arb_with_web()
        )

def run_web_server():
    """Run web server in a separate thread"""
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

async def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         MegaETH Alpha Suite - Full System                ║
    ║                                                          ║
    ║  🤖 Bot: Running all modules                             ║
    ║  🌐 Web: http://localhost:8000                           ║
    ║                                                          ║
    ║  Press CTRL+C to stop                                    ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Start web server in background thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    # Give web server time to start
    await asyncio.sleep(2)
    
    # Run bots
    bot = BotWithWebIntegration()
    await bot.run_all_bots()

if __name__ == "__main__":
    asyncio.run(main())

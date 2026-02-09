#!/usr/bin/env python3
"""
MegaETH Alpha Suite - Main Entry Point
Multi-tool suite for MegaETH trading
"""

import asyncio
import json
import signal
import sys
from pathlib import Path
from colorama import init, Fore, Style

from src.scanner.token_scanner import TokenScanner
from src.tracker.wallet_tracker import WalletTracker
from src.trader.sniper import Sniper
from src.trader.copy_trader import CopyTrader
from src.arbitrage.arb_detector import ArbDetector
from src.alerts.telegram_bot import TelegramAlert
from src.analyzer.contract_analyzer import ContractAnalyzer

init(autoreset=True)

class AlphaSuite:
    def __init__(self):
        self.config = self.load_config()
        self.wallets_config = self.load_wallets()
        self.running = True
        
        # Initialize modules
        self.alerts = TelegramAlert(self.config['alerts'])
        self.analyzer = ContractAnalyzer(self.config['network'])
        self.scanner = TokenScanner(self.config, self.analyzer, self.alerts)
        self.tracker = WalletTracker(self.config, self.wallets_config, self.alerts)
        self.sniper = Sniper(self.config, self.analyzer, self.alerts)
        self.copy_trader = CopyTrader(self.config, self.wallets_config, self.alerts)
        self.arb_detector = ArbDetector(self.config, self.alerts)
        
    def load_config(self) -> dict:
        config_path = Path(__file__).parent / "config" / "settings.json"
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def load_wallets(self) -> dict:
        wallets_path = Path(__file__).parent / "config" / "wallets.json"
        with open(wallets_path, 'r') as f:
            return json.load(f)
    
    def print_banner(self):
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║  {Fore.YELLOW}███╗   ███╗███████╗ ██████╗  █████╗ {Fore.CYAN}                        ║
║  {Fore.YELLOW}████╗ ████║██╔════╝██╔════╝ ██╔══██╗{Fore.CYAN}                        ║
║  {Fore.YELLOW}██╔████╔██║█████╗  ██║  ███╗███████║{Fore.CYAN}  {Fore.WHITE}Alpha Suite{Fore.CYAN}          ║
║  {Fore.YELLOW}██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║{Fore.CYAN}  {Fore.GREEN}MegaETH Tools{Fore.CYAN}        ║
║  {Fore.YELLOW}██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║{Fore.CYAN}                        ║
║  {Fore.YELLOW}╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝{Fore.CYAN}                        ║
╚══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""
        print(banner)
    
    def print_menu(self):
        menu = f"""
{Fore.WHITE}Select mode:{Style.RESET_ALL}
  {Fore.GREEN}[1]{Style.RESET_ALL} Token Scanner      - Detect new tokens
  {Fore.GREEN}[2]{Style.RESET_ALL} Wallet Tracker     - Track whale wallets
  {Fore.GREEN}[3]{Style.RESET_ALL} Sniper Bot         - Auto-buy new tokens
  {Fore.GREEN}[4]{Style.RESET_ALL} Copy Trader        - Copy whale trades
  {Fore.GREEN}[5]{Style.RESET_ALL} Arbitrage Detector - Find arb opportunities
  {Fore.GREEN}[6]{Style.RESET_ALL} Full Auto Mode     - Run all modules
  {Fore.RED}[0]{Style.RESET_ALL} Exit
"""
        print(menu)
    
    async def run_scanner(self):
        print(f"{Fore.CYAN}[*] Starting Token Scanner...{Style.RESET_ALL}")
        await self.scanner.start()
    
    async def run_tracker(self):
        print(f"{Fore.CYAN}[*] Starting Wallet Tracker...{Style.RESET_ALL}")
        await self.tracker.start()
    
    async def run_sniper(self):
        print(f"{Fore.CYAN}[*] Starting Sniper Bot...{Style.RESET_ALL}")
        await self.sniper.start()
    
    async def run_copy_trader(self):
        print(f"{Fore.CYAN}[*] Starting Copy Trader...{Style.RESET_ALL}")
        await self.copy_trader.start()
    
    async def run_arbitrage(self):
        print(f"{Fore.CYAN}[*] Starting Arbitrage Detector...{Style.RESET_ALL}")
        await self.arb_detector.start()
    
    async def run_full_auto(self):
        print(f"{Fore.YELLOW}[*] Starting Full Auto Mode...{Style.RESET_ALL}")
        await asyncio.gather(
            self.scanner.start(),
            self.tracker.start(),
            self.arb_detector.start()
        )
    
    async def main(self):
        self.print_banner()
        
        while self.running:
            self.print_menu()
            try:
                choice = input(f"{Fore.YELLOW}> {Style.RESET_ALL}").strip()
                
                if choice == '1':
                    await self.run_scanner()
                elif choice == '2':
                    await self.run_tracker()
                elif choice == '3':
                    await self.run_sniper()
                elif choice == '4':
                    await self.run_copy_trader()
                elif choice == '5':
                    await self.run_arbitrage()
                elif choice == '6':
                    await self.run_full_auto()
                elif choice == '0':
                    print(f"{Fore.RED}[*] Exiting...{Style.RESET_ALL}")
                    self.running = False
                else:
                    print(f"{Fore.RED}[!] Invalid choice{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.RED}[*] Interrupted. Exiting...{Style.RESET_ALL}")
                self.running = False

def main():
    suite = AlphaSuite()
    asyncio.run(suite.main())

if __name__ == "__main__":
    main()

"""
Telegram Alert System - Send notifications via Telegram
"""

import asyncio
import aiohttp
from typing import Optional
from colorama import Fore, Style


class TelegramAlert:
    def __init__(self, alerts_config: dict):
        self.bot_token = alerts_config.get('telegram_bot_token', '')
        self.chat_id = alerts_config.get('telegram_chat_id', '')
        self.discord_webhook = alerts_config.get('discord_webhook_url', '')
        
        self.enabled = self.bot_token and self.chat_id and \
                       self.bot_token != "YOUR_TELEGRAM_BOT_TOKEN" and \
                       self.chat_id != "YOUR_CHAT_ID"
        
        if not self.enabled:
            print(f"{Fore.YELLOW}[Alerts] Telegram not configured - alerts disabled{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}[Alerts] Telegram alerts enabled{Style.RESET_ALL}")
    
    async def send(self, message: str, parse_mode: str = "Markdown"):
        """Send a message via Telegram"""
        if not self.enabled:
            return
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error = await response.text()
                        print(f"{Fore.RED}[Alerts] Telegram error: {error}{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}[Alerts] Failed to send Telegram: {e}{Style.RESET_ALL}")
    
    async def send_discord(self, message: str):
        """Send a message via Discord webhook"""
        if not self.discord_webhook:
            return
        
        try:
            payload = {
                "content": message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.discord_webhook, json=payload) as response:
                    if response.status not in [200, 204]:
                        print(f"{Fore.RED}[Alerts] Discord error: {response.status}{Style.RESET_ALL}")
                        
        except Exception as e:
            print(f"{Fore.RED}[Alerts] Failed to send Discord: {e}{Style.RESET_ALL}")
    
    async def send_all(self, message: str):
        """Send message to all configured channels"""
        tasks = [self.send(message)]
        
        if self.discord_webhook:
            tasks.append(self.send_discord(message))
        
        await asyncio.gather(*tasks)
    
    async def test(self):
        """Send a test message"""
        test_message = """
🧪 **TEST ALERT**

MegaETH Alpha Suite is connected!
Alerts are working correctly.
"""
        await self.send(test_message)
        print(f"{Fore.GREEN}[Alerts] Test message sent{Style.RESET_ALL}")

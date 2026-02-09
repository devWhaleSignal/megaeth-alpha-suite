# MegaETH Alpha Suite 🚀

Suite d'outils de trading pour MegaETH - Token Scanner, Wallet Tracker, Sniper, Copy Trading, Arbitrage.

## Installation

```bash
# 1. Installer Python 3.10+
# 2. Installer les dépendances
pip install -r requirements.txt
```

## Configuration

### 1. Éditer `config/settings.json`

```json
{
  "network": {
    "rpc_url": "https://rpc.megaeth.com"  // RPC MegaETH
  },
  "wallet": {
    "private_key": "YOUR_PRIVATE_KEY",    // ⚠️ Ne jamais partager
    "address": "0xYOUR_ADDRESS"
  },
  "trading": {
    "max_buy_amount_eth": 0.1,            // Max par trade
    "slippage_percent": 5
  },
  "alerts": {
    "telegram_bot_token": "BOT_TOKEN",    // @BotFather
    "telegram_chat_id": "CHAT_ID"         // @userinfobot
  }
}
```

### 2. Ajouter des wallets à tracker

Éditer `config/wallets.json`:
```json
{
  "tracked_wallets": [
    {
      "address": "0xWHALE_ADDRESS",
      "label": "Whale #1",
      "copy_trade": true,
      "alert_on_trade": true
    }
  ]
}
```

## Lancement

```bash
python main.py
```

## Modules

| Module | Description |
|--------|-------------|
| **Token Scanner** | Détecte les nouveaux tokens déployés |
| **Wallet Tracker** | Surveille les wallets de whales |
| **Sniper Bot** | Achat automatique de nouveaux tokens |
| **Copy Trader** | Copie les trades des wallets trackés |
| **Arbitrage** | Détecte les opportunités d'arbitrage |

## ⚠️ Avertissements

- **Ne jamais partager ta clé privée**
- **Utiliser un wallet dédié** avec seulement les fonds que tu peux perdre
- **Tester d'abord** avec de petits montants
- **Les adresses DEX** doivent être mises à jour quand les DEX seront live sur MegaETH

## TODO (à implémenter)

- [ ] Mettre à jour les adresses DEX (router, factory, WETH) quand disponibles
- [ ] Ajouter la simulation de buy/sell pour détecter les taxes
- [ ] Implémenter le calcul réel de liquidité
- [ ] Ajouter plus de DEX dans l'arbitrage

## Structure

```
MegaETH-Alpha-Suite/
├── config/
│   ├── settings.json      # Configuration principale
│   └── wallets.json       # Wallets à tracker
├── src/
│   ├── scanner/           # Détection nouveaux tokens
│   ├── tracker/           # Wallet tracking
│   ├── trader/            # Sniper + Copy trade
│   ├── analyzer/          # Analyse sécurité contrats
│   ├── arbitrage/         # Détection arbitrage
│   └── alerts/            # Notifications Telegram/Discord
├── main.py                # Point d'entrée
├── requirements.txt
└── README.md
```

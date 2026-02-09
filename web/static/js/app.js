/**
 * MegaETH Alpha Suite - Frontend
 */

class AlphaSuite {
    constructor() {
        this.ws = null;
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupFilters();
        this.loadStats();
    }

    connectWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${location.host}/ws`);
        
        this.ws.onopen = () => {
            console.log('Connected');
            document.querySelector('.status-dot')?.classList.add('online');
            setInterval(() => this.ws.readyState === 1 && this.ws.send('ping'), 30000);
        };
        
        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                this.handleUpdate(data);
            } catch {}
        };
        
        this.ws.onclose = () => {
            document.querySelector('.status-dot')?.classList.remove('online');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleUpdate(data) {
        switch(data.type) {
            case 'new_token': this.addToken(data.data); break;
            case 'new_trade': this.addTrade(data.data); break;
            case 'new_arb': this.addArb(data.data); break;
        }
    }

    addToken(token) {
        this.incrementStat('tokens-scanned');
        
        const container = document.getElementById('latest-tokens');
        if (container) {
            this.clearEmpty(container);
            container.insertAdjacentHTML('afterbegin', `
                <div class="list-item new-item">
                    <div class="item-main">
                        <span class="item-symbol">${token.info?.symbol || '???'}</span>
                        <span class="item-name">${token.info?.name || 'Unknown'}</span>
                    </div>
                    <span class="badge ${token.security?.safe ? 'safe' : 'danger'}">${token.security?.safe ? 'SAFE' : 'RISKY'}</span>
                </div>
            `);
            this.trimList(container, 5);
        }
        
        const tbody = document.getElementById('tokens-tbody');
        if (tbody) {
            const emptyRow = tbody.querySelector('.empty');
            if (emptyRow) emptyRow.parentElement.remove();
            
            tbody.insertAdjacentHTML('afterbegin', `
                <tr class="new-item">
                    <td class="mono">${new Date().toLocaleTimeString()}</td>
                    <td>${token.info?.name || 'Unknown'}</td>
                    <td class="bold">${token.info?.symbol || '???'}</td>
                    <td class="mono dim">${token.address?.slice(0,10)}...${token.address?.slice(-8)}</td>
                    <td>$${(token.liquidity || 0).toFixed(2)}</td>
                    <td><span class="badge ${token.security?.safe ? 'safe' : 'danger'}">${token.security?.safe ? 'SAFE' : 'RISKY'}</span></td>
                    <td><a href="https://explorer.megaeth.com/token/${token.address}" target="_blank" class="btn-sm">View</a></td>
                </tr>
            `);
        }
    }

    addTrade(trade) {
        this.incrementStat('trades-detected');
        
        const container = document.getElementById('latest-trades');
        if (container) {
            this.clearEmpty(container);
            container.insertAdjacentHTML('afterbegin', `
                <div class="list-item new-item">
                    <div class="item-main">
                        <span class="item-wallet">${trade.wallet?.label || 'Unknown'}</span>
                        <span class="badge ${trade.type === 'BUY' ? 'buy' : 'sell'}">${trade.type}</span>
                    </div>
                    <span class="item-amount">${trade.amount || '?'} ETH</span>
                </div>
            `);
            this.trimList(container, 5);
        }
        
        const tbody = document.getElementById('whales-tbody');
        if (tbody) {
            const emptyRow = tbody.querySelector('.empty');
            if (emptyRow) emptyRow.parentElement.remove();
            
            tbody.insertAdjacentHTML('afterbegin', `
                <tr class="new-item">
                    <td class="mono">${new Date().toLocaleTimeString()}</td>
                    <td><span class="wallet-name">${trade.wallet?.label || 'Unknown'}</span><span class="wallet-addr mono dim">${trade.wallet?.address?.slice(0,8)}...</span></td>
                    <td><span class="badge ${trade.type === 'BUY' ? 'buy' : 'sell'}">${trade.type}</span></td>
                    <td>${trade.token || 'ETH'}</td>
                    <td class="bold">${trade.amount} ETH</td>
                    <td><a href="https://explorer.megaeth.com/tx/${trade.tx_hash}" target="_blank" class="btn-sm">View</a></td>
                </tr>
            `);
        }
    }

    addArb(arb) {
        this.incrementStat('arb-found');
        
        const container = document.getElementById('latest-arbs');
        if (container) {
            this.clearEmpty(container);
            container.insertAdjacentHTML('afterbegin', `
                <div class="list-item new-item">
                    <div class="item-main">
                        <span class="mono">${arb.buy_dex?.toUpperCase()} → ${arb.sell_dex?.toUpperCase()}</span>
                    </div>
                    <span class="arb-profit">+${arb.profit_percent?.toFixed(2)}%</span>
                </div>
            `);
            this.trimList(container, 3);
        }
        
        const grid = document.getElementById('arb-grid');
        if (grid) {
            const empty = grid.querySelector('.empty-state');
            if (empty) empty.remove();
            
            grid.insertAdjacentHTML('afterbegin', `
                <div class="arb-card new-item">
                    <div class="arb-header">
                        <span class="arb-pair mono">${arb.base_token?.slice(0,6)}../${arb.quote_token?.slice(0,6)}..</span>
                        <span class="arb-profit">+${arb.profit_percent?.toFixed(2)}%</span>
                    </div>
                    <div class="arb-body">
                        <div class="arb-step buy">
                            <span class="step-label">BUY</span>
                            <span class="step-dex">${arb.buy_dex?.toUpperCase()}</span>
                            <span class="step-price mono">${arb.buy_price?.toFixed(8)}</span>
                        </div>
                        <div class="arb-arrow"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg></div>
                        <div class="arb-step sell">
                            <span class="step-label">SELL</span>
                            <span class="step-dex">${arb.sell_dex?.toUpperCase()}</span>
                            <span class="step-price mono">${arb.sell_price?.toFixed(8)}</span>
                        </div>
                    </div>
                    <div class="arb-footer mono">${new Date().toLocaleTimeString()}</div>
                </div>
            `);
        }
    }

    clearEmpty(container) {
        const empty = container.querySelector('.empty-state');
        if (empty) empty.remove();
    }

    trimList(container, max) {
        while (container.children.length > max) {
            container.lastElementChild.remove();
        }
    }

    incrementStat(id) {
        const el = document.getElementById(id);
        if (el) {
            const val = parseInt(el.textContent) || 0;
            el.textContent = val + 1;
        }
    }

    async loadStats() {
        try {
            const stats = await fetch('/api/stats').then(r => r.json());
            const ids = ['tokens-scanned', 'trades-detected', 'arb-found'];
            ids.forEach(id => {
                const el = document.getElementById(id);
                const key = id.replace('-', '_');
                if (el && stats[key] !== undefined) el.textContent = stats[key];
            });
        } catch {}
    }

    setupFilters() {
        const tokenSearch = document.getElementById('token-search');
        if (tokenSearch) {
            tokenSearch.addEventListener('input', (e) => this.filterTable('tokens-table', e.target.value));
        }
        
        const whaleSearch = document.getElementById('whale-search');
        if (whaleSearch) {
            whaleSearch.addEventListener('input', (e) => this.filterTable('whales-table', e.target.value));
        }
    }

    filterTable(tableId, query) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const rows = table.querySelectorAll('tbody tr');
        const q = query.toLowerCase();
        
        rows.forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
    }
}

// CSS for list items (injected)
const style = document.createElement('style');
style.textContent = `
.list-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}
.list-item:last-child { border-bottom: none; }
.item-main { display: flex; align-items: center; gap: 0.75rem; }
.item-symbol { font-weight: 600; }
.item-name { color: var(--text-dim); font-size: 0.875rem; }
.item-wallet { font-weight: 500; }
.item-amount { font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; }
.list-item .arb-profit { color: var(--green); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
`;
document.head.appendChild(style);

// Init
document.addEventListener('DOMContentLoaded', () => new AlphaSuite());

import { DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ChartConfiguration } from 'chart.js';
import { forkJoin } from 'rxjs';
import { ApiService } from '../core/api.service';
import { DrawdownResult, ExitReasons, Filters, HoldingTime, Summary } from '../core/models';
import { AccountSummaryComponent } from '../shared/account-summary.component';
import { BotStatusComponent } from '../shared/bot-status.component';
import { ChartComponent } from '../shared/chart.component';
import { FilterBarComponent } from '../shared/filter-bar.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [FilterBarComponent, ChartComponent, DecimalPipe, AccountSummaryComponent, BotStatusComponent],
  template: `
    <app-bot-status />
    <app-account-summary />
    <h2>Performance Dashboard</h2>
    <app-filter-bar (changed)="load($event)" />
    @if (error) { <p class="err">{{ error }}</p> }
    @if (summary) {
      <div class="cards">
        <div class="card"><span>Trades</span><b>{{ summary.trades }}</b></div>
        <div class="card"><span>Win Rate</span><b>{{ summary.win_rate | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Profit Factor</span><b>{{ summary.profit_factor === null ? '∞ / n/a' : (summary.profit_factor | number: '1.2-2') }}</b></div>
        <div class="card"><span>Total P&amp;L</span><b>{{ summary.total_pnl | number: '1.2-2' }}</b></div>
        <div class="card"><span>Average Hold (Min)</span><b>{{ holding?.overall?.avg_minutes | number: '1.0-0' }}</b></div>
        <div class="card"><span>Take Profit Hit</span><b>{{ exits?.take_profit?.pct | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Stop Loss Hit</span><b>{{ exits?.stop_loss?.pct | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Max Drawdown</span>
          <b>{{ dd?.max_drawdown | number: '1.2-2' }}@if (dd?.max_drawdown_pct !== null) { ({{ dd?.max_drawdown_pct }}%) }</b></div>
        <div class="card"><span>Avg Trades per Day</span><b>{{ summary.avg_trades_per_day | number: '1.1-1' }}</b></div>
      </div>
    }
    <div class="grid">
      @if (equity) { <section class="wide"><h3>Equity &amp; Drawdown</h3><app-chart [config]="equity" /></section> }
    </div>`,
  styles: [`
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .75rem; margin-bottom: 1.5rem; }
    .card { background: #f4f6f8; border-radius: 8px; padding: .75rem; display: flex; flex-direction: column; }
    .card span { font-size: .75rem; color: #666; } .card b { font-size: 1.3rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 1.5rem; }
    .wide { grid-column: 1 / -1; } .err { color: #c0392b; }`],
})
export class DashboardComponent {
  private api = inject(ApiService);
  summary?: Summary; holding?: HoldingTime; exits?: ExitReasons; dd?: DrawdownResult;
  equity?: ChartConfiguration;
  error = '';

  load(f: Filters) {
    forkJoin({
      summary: this.api.summary(f), holding: this.api.holdingTime(f), exits: this.api.exitReasons(f),
      dd: this.api.drawdown(f),
    }).subscribe({
      next: (r) => {
        this.error = '';
        this.summary = r.summary; this.holding = r.holding; this.exits = r.exits; this.dd = r.dd;
        const labels = r.dd.curve.map((p) => p.time.slice(0, 16).replace('T', ' '));
        this.equity = {
          type: 'line',
          data: {
            labels,
            datasets: [
              { label: 'Equity', data: r.dd.curve.map((p) => p.equity), borderColor: '#16a34a', tension: 0.2 },
              { label: 'Drawdown', data: r.dd.curve.map((p) => -p.drawdown), borderColor: '#dc2626',
                backgroundColor: 'rgba(220,38,38,.15)', fill: true, tension: 0.2 },
            ],
          },
          options: {
            scales: {
              x: {
                grid: { display: false },
                ticks: {
                  autoSkip: false,
                  maxRotation: 0,
                  callback: (_value, index) => {
                    const date = labels[index]?.slice(0, 10) ?? '';
                    const previousDate = index > 0 ? labels[index - 1]?.slice(0, 10) : undefined;
                    return date !== previousDate
                      ? new Date(`${date}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
                      : '';
                  },
                },
              },
            },
          },
        };
      },
      error: () => (this.error = 'Could not load analytics from the API.'),
    });
  }

}

import { DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ChartConfiguration } from 'chart.js';
import { forkJoin } from 'rxjs';
import { ApiService } from '../core/api.service';
import { DrawdownResult, ExitReasons, Filters, GroupStat, HoldingTime, AtrBucket, Summary } from '../core/models';
import { ChartComponent } from '../shared/chart.component';
import { FilterBarComponent } from '../shared/filter-bar.component';

const bar = (labels: string[], data: (number | null)[], label: string, color = '#3b82f6'): ChartConfiguration => ({
  type: 'bar',
  data: { labels, datasets: [{ label, data, backgroundColor: color }] },
  options: { scales: { y: { beginAtZero: true } } },
});

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [FilterBarComponent, ChartComponent, DecimalPipe],
  template: `
    <h2>Performance dashboard</h2>
    <app-filter-bar (changed)="load($event)" />
    @if (error) { <p class="err">{{ error }}</p> }
    @if (summary) {
      <div class="cards">
        <div class="card"><span>Trades</span><b>{{ summary.trades }}</b></div>
        <div class="card"><span>Win rate</span><b>{{ summary.win_rate | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Profit factor</span><b>{{ summary.profit_factor === null ? '∞ / n/a' : (summary.profit_factor | number: '1.2-2') }}</b></div>
        <div class="card"><span>Total P&amp;L</span><b>{{ summary.total_pnl | number: '1.2-2' }}</b></div>
        <div class="card"><span>Avg hold (min)</span><b>{{ holding?.overall?.avg_minutes | number: '1.0-0' }}</b></div>
        <div class="card"><span>Take profit hit</span><b>{{ exits?.take_profit?.pct | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Stop loss hit</span><b>{{ exits?.stop_loss?.pct | number: '1.1-1' }}%</b></div>
        <div class="card"><span>Max drawdown</span>
          <b>{{ dd?.max_drawdown | number: '1.2-2' }}@if (dd?.max_drawdown_pct !== null) { ({{ dd?.max_drawdown_pct }}%) }</b></div>
      </div>
    }
    <div class="grid">
      @if (equity) { <section class="wide"><h3>Equity &amp; drawdown</h3><app-chart [config]="equity" /></section> }
      @if (pair) { <section><h3>Win rate by pair (%)</h3><app-chart [config]="pair" /></section> }
      @if (session) { <section><h3>Win rate by session (%)</h3><app-chart [config]="session" /></section> }
      @if (direction) { <section><h3>Long vs short — P&amp;L</h3><app-chart [config]="direction" /></section> }
      <section><h3>Win rate by ATR range (%)</h3>
        @if (atr) { <app-chart [config]="atr" /> } @else { <p>No ATR data yet — signals are not being recorded by the bot.</p> }
      </section>
    </div>`,
  styles: [`
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .75rem; margin-bottom: 1.5rem; }
    .card { background: #f4f6f8; border-radius: 8px; padding: .75rem; display: flex; flex-direction: column; }
    .card span { font-size: .75rem; color: #666; } .card b { font-size: 1.3rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; }
    .wide { grid-column: 1 / -1; } .err { color: #c0392b; }`],
})
export class DashboardComponent {
  private api = inject(ApiService);
  summary?: Summary; holding?: HoldingTime; exits?: ExitReasons; dd?: DrawdownResult;
  equity?: ChartConfiguration; pair?: ChartConfiguration; session?: ChartConfiguration;
  direction?: ChartConfiguration; atr?: ChartConfiguration;
  error = '';

  load(f: Filters) {
    forkJoin({
      summary: this.api.summary(f), holding: this.api.holdingTime(f), exits: this.api.exitReasons(f),
      dd: this.api.drawdown(f), pair: this.api.byInstrument(f), session: this.api.bySession(f),
      direction: this.api.byDirection(f), atr: this.api.atrRanges(f),
    }).subscribe({
      next: (r) => {
        this.error = '';
        this.summary = r.summary; this.holding = r.holding; this.exits = r.exits; this.dd = r.dd;
        this.equity = {
          type: 'line',
          data: {
            labels: r.dd.curve.map((p) => p.time.slice(0, 16).replace('T', ' ')),
            datasets: [
              { label: 'Equity', data: r.dd.curve.map((p) => p.equity), borderColor: '#16a34a', tension: 0.2 },
              { label: 'Drawdown', data: r.dd.curve.map((p) => -p.drawdown), borderColor: '#dc2626',
                backgroundColor: 'rgba(220,38,38,.15)', fill: true, tension: 0.2 },
            ],
          },
        };
        this.pair = this.winRate(r.pair, 'instrument');
        this.session = this.winRate(r.session, 'session');
        const dirs = r.direction;
        this.direction = bar(dirs.map((d) => String(d['direction'])), dirs.map((d) => d.total_pnl), 'P&L', '#8b5cf6');
        this.atr = r.atr.length ? this.atrChart(r.atr) : undefined;
      },
      error: () => (this.error = 'Could not load analytics from the API.'),
    });
  }

  private winRate(rows: GroupStat[], key: string) {
    return bar(rows.map((r) => `${r[key]} (${r.trades})`), rows.map((r) => r.win_rate), 'Win rate %');
  }

  private atrChart(rows: AtrBucket[]) {
    return bar(rows.map((r) => `${r.atr_min}–${r.atr_max} (${r.trades})`), rows.map((r) => r.win_rate), 'Win rate %', '#f59e0b');
  }
}

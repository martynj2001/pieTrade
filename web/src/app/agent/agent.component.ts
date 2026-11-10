import { DatePipe, DecimalPipe, TitleCasePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { AgentComparison, AgentDecisionPage, AgentMode, AgentReport, AgentReportAvailable } from '../core/models';
import { ApiService } from '../core/api.service';

interface MetricRow {
  label: string;
  efficiency: number | null;
  range: number | null;
}

@Component({
  selector: 'app-agent',
  standalone: true,
  imports: [DatePipe, DecimalPipe, FormsModule, RouterLink, TitleCasePipe],
  template: `
    <h2>Agent</h2>
    <a class="guide" routerLink="/agent/outcomes">View Outcomes Guide</a>
    <div class="filters">
      <label>Mode
        <select [(ngModel)]="mode" (ngModelChange)="onMode($event)">
          <option value="all">All</option><option value="shadow">Shadow</option><option value="live">Live</option>
        </select>
      </label>
      <label>Period
        <select [(ngModel)]="period" (ngModelChange)="onPeriod($event)">
          <option value="7">7 Days</option><option value="14">14 Days</option>
          <option value="30">30 Days</option><option value="all">All</option>
        </select>
      </label>
      <button type="button" (click)="refresh()" [disabled]="loading">Refresh</button>
    </div>

    @if (loading) { <p>Loading Agent Analysis…</p> }
    @if (error) { <p class="err">{{ error }}</p> }
    @if (unavailableMessage; as message) {
      <section class="info">{{ message }}</section>
    }
    @if (availableReport; as data) {
      <section class="card readiness" [class.ready]="data.go_live.ready" [class.not-ready]="!data.go_live.ready">
        <h3>Go-Live Readiness</h3>
        <strong class="banner">{{ data.go_live.ready ? 'READY' : 'NOT YET' }}</strong>
        <div class="table-wrap"><table><thead><tr><th>Check</th><th>Result</th><th>Value</th><th>Target</th></tr></thead>
          <tbody>@for (check of data.go_live.checks; track check.name) {
            <tr><td>{{ check.name | titlecase }}</td><td><span class="badge" [class.pass]="check.passed" [class.fail]="!check.passed">{{ check.passed ? 'PASS' : 'FAIL' }}</span></td><td>{{ check.value }}</td><td>{{ check.target }}</td></tr>
          }</tbody>
        </table></div>
      </section>

      <div class="cards">
        <section class="card">
          <h3>Reliability</h3>
          <div class="stats"><span>Successful <b>{{ data.reliability.ok_pct === null ? '-' : (data.reliability.ok_pct | number: '1.1-1') + '%' }}</b></span>
            <span>Average Latency <b>{{ data.reliability.avg_latency_s === null ? '-' : (data.reliability.avg_latency_s | number: '1.2-2') + ' s' }}</b></span>
            <span>Total Decisions <b>{{ data.reliability.total }}</b></span></div>
          <div class="table-wrap"><table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>
            @for (row of data.reliability.by_status; track row.status) { <tr><td>{{ row.status }}</td><td>{{ row.count }}</td></tr> }
          </tbody></table></div>
        </section>
        <section class="card">
          <h3>Agreement</h3>
          <p>Compared Hours: <b>{{ data.agreement.n }}</b></p>
          <p>Same as Fixed: <b>{{ data.agreement.pct_same_as_fixed === null ? '-' : (data.agreement.pct_same_as_fixed | number: '1.1-1') + '%' }}</b></p>
          <p>Same as Baseline: <b>{{ data.agreement.pct_same_as_baseline === null ? '-' : (data.agreement.pct_same_as_baseline | number: '1.1-1') + '%' }}</b></p>
        </section>
      </div>

      <section class="card">
        <h3>Agent vs Fixed vs Baseline</h3>
        <p class="explanation">Efficiency = net move / total range in the hour (1 = clean trend, 0 = went nowhere)<br>Range/ATR = hour's range vs normal candle size</p>
        <div class="table-wrap"><table><thead><tr><th>Pair</th><th>Average Efficiency</th><th>Average Range/ATR</th></tr></thead><tbody>
          @for (row of mainRows; track row.label) { <tr><td>{{ row.label }}</td><td>{{ row.efficiency === null ? '-' : (row.efficiency | number: '1.3-3') }}</td><td>{{ row.range === null ? '-' : (row.range | number: '1.2-2') }}</td></tr> }
        </tbody></table></div>
        <p>Agent Beats Fixed / Baseline: <b>{{ percent(data.comparison.pct_beats_fixed_eff) }} / {{ percent(data.comparison.pct_beats_base_eff) }}</b> of hours</p>
      </section>

      <section class="card">
        <h3>Hours Where the Agent Differed from the Fixed Pair</h3>
        <div class="table-wrap"><table><thead><tr><th>Pair</th><th>Average Efficiency</th><th>Average Range/ATR</th></tr></thead><tbody>
          @for (row of disagreementRows; track row.label) { <tr><td>{{ row.label }}</td><td>{{ row.efficiency === null ? '-' : (row.efficiency | number: '1.3-3') }}</td><td>{{ row.range === null ? '-' : (row.range | number: '1.2-2') }}</td></tr> }
        </tbody></table></div>
        <p>Agent Beats Fixed / Baseline: <b>{{ percent(data.disagreements.pct_beats_fixed_eff) }} / {{ percent(data.disagreements.pct_beats_base_eff) }}</b> of hours</p>
      </section>

      <section class="card">
        <h3>By Market</h3>
        <div class="table-wrap"><table><thead><tr><th>Market</th><th>Hours</th><th>Agent Eff</th><th>Fixed Eff</th><th>Baseline Eff</th><th>Any Eff</th><th>Agent Range/ATR</th><th>Fixed Range/ATR</th><th>Baseline Range/ATR</th><th>Any Range/ATR</th></tr></thead>
          <tbody>@for (row of data.by_market; track row.market) { <tr><td>{{ row.market }}</td><td>{{ row.n }}</td><td>{{ fixed(row.agent_eff, 3) }}</td><td>{{ fixed(row.fixed_eff, 3) }}</td><td>{{ fixed(row.base_eff, 3) }}</td><td>{{ fixed(row.any_eff, 3) }}</td><td>{{ fixed(row.agent_range_atr, 2) }}</td><td>{{ fixed(row.fixed_range_atr, 2) }}</td><td>{{ fixed(row.base_range_atr, 2) }}</td><td>{{ fixed(row.any_range_atr, 2) }}</td></tr> }</tbody>
        </table></div>
      </section>

      <div class="cards">
        <section class="card"><h3>News</h3>
          <div class="stats"><span>Decisions With News Exclusions <b>{{ data.news_cost.decisions_with_news_exclusion }}</b></span></div>
        </section>
        <section class="card"><h3>Cost</h3>
          <div class="stats"><span>Input Tokens <b>{{ data.news_cost.input_tokens }}</b></span>
            <span>Output Tokens <b>{{ data.news_cost.output_tokens }}</b></span>
            <span>Estimated Cost <b>£{{ data.news_cost.est_cost_gbp | number: '1.4-4' }}</b></span></div>
        </section>
      </div>

      @if (data.live_pnl.length) {
        <section class="card"><h3>Live P&amp;L</h3>
          <div class="table-wrap"><table><thead><tr><th>Market</th><th>Trades</th><th>P&amp;L</th><th>Win %</th></tr></thead><tbody>
            @for (row of data.live_pnl; track row.market) { <tr><td>{{ row.market ?? '-' }}</td><td>{{ row.trades }}</td><td>{{ row.pnl === null ? '-' : (row.pnl | number: '1.2-2') }}</td><td>{{ row.win_pct === null ? '-' : (row.win_pct | number: '1.1-1') + '%' }}</td></tr> }
          </tbody></table></div>
        </section>
      }

      <section class="card">
        <h3>Latest Decisions</h3>
        <div class="table-wrap"><table><thead><tr><th>Target Hour</th><th>Mode</th><th>Status</th><th>Agent Pick</th><th>Fixed</th><th>Baseline</th><th>Reason</th></tr></thead>
          <tbody>@for (row of decisions?.items ?? []; track row.id) { <tr><td>{{ row.target_hour | date: 'yyyy-MM-dd HH:mm' }}</td><td>{{ row.mode }}</td><td>{{ row.status }}</td><td>{{ row.instrument ?? '-' }}</td><td>{{ row.fixed_instrument ?? '-' }}</td><td>{{ row.baseline_instrument ?? '-' }}</td><td>{{ row.reason ?? '-' }}</td></tr> }
            @empty { <tr><td colspan="7">No Decisions.</td></tr> }
          </tbody>
        </table></div>
        <div class="pager"><button type="button" (click)="page(-1)" [disabled]="offset === 0 || loading">Prev</button>
          <span>{{ decisions?.items?.length ? offset + 1 : 0 }}–{{ offset + (decisions?.items?.length ?? 0) }} of {{ decisions?.total ?? 0 }}</span>
          <button type="button" (click)="page(1)" [disabled]="!decisions || offset + limit >= decisions.total || loading">Next</button>
        </div>
      </section>
      <p class="note">Proxies for trendiness, not profit.</p>
    }
  `,
  styles: [`
    .filters { display: flex; flex-wrap: wrap; gap: .75rem; align-items: end; margin-bottom: 1rem; }
    label { display: flex; flex-direction: column; font-size: .8rem; color: #555; gap: .2rem; }
    select, button { padding: .35rem .5rem; }
    .card, .info { background: #f4f6f8; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 1rem; }
    .cards .card { margin-bottom: 0; }
    h3 { margin: 0 0 .75rem; font-size: 1rem; }
    table { border-collapse: collapse; width: 100%; font-size: .9rem; }
    th, td { padding: .4rem .6rem; border-bottom: 1px solid #ddd; text-align: left; vertical-align: top; }
    th { background: #edf0f3; white-space: nowrap; }
    .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .stats { display: flex; flex-wrap: wrap; gap: .75rem 1.25rem; margin-bottom: .75rem; }
    .stats span { display: flex; flex-direction: column; gap: .2rem; color: #555; font-size: .85rem; }
    .stats b { color: #111; font-size: 1.05rem; }
    .readiness { border-left: 4px solid #c0392b; }
    .readiness.ready { border-color: #16803c; }
    .banner { display: inline-block; margin-bottom: .75rem; padding: .35rem .6rem; border-radius: 4px; background: #fce8e6; color: #a12622; }
    .ready .banner { background: #e4f4e9; color: #126530; }
    .badge { display: inline-block; border-radius: 4px; padding: .15rem .4rem; font-weight: 700; font-size: .75rem; }
    .pass { background: #e4f4e9; color: #126530; } .fail { background: #fce8e6; color: #a12622; }
    .explanation { color: #555; line-height: 1.5; }
    .pager { display: flex; gap: 1rem; align-items: center; margin-top: 1rem; }
    .pager button { min-height: 44px; }
    .guide { display: inline-block; margin: 0 0 1rem; }
    .err { color: #c0392b; } .note { color: #555; font-size: .85rem; }
    @media (max-width: 640px) { .card { padding: .75rem; } }
  `],
})
export class AgentComponent {
  private api = inject(ApiService);
  mode: AgentMode = 'all';
  period = '14';
  report: AgentReport | null = null;
  decisions: AgentDecisionPage | null = null;
  loading = false;
  error = '';
  limit = 50;
  offset = 0;

  get days(): number | undefined { return this.period === 'all' ? undefined : Number(this.period); }

  get availableReport(): AgentReportAvailable | null {
    return this.report?.available ? this.report : null;
  }

  get unavailableMessage(): string | null {
    return this.report?.available === false ? this.report.message : null;
  }

  get mainRows(): MetricRow[] {
    return this.report?.available ? this.metricRows(this.report.comparison) : [];
  }

  get disagreementRows(): MetricRow[] {
    return this.report?.available ? this.metricRows(this.report.disagreements) : [];
  }

  constructor() { this.refresh(); }

  onMode(mode: AgentMode) { this.mode = mode; this.offset = 0; this.refresh(); }
  onPeriod(period: string) { this.period = period; this.offset = 0; this.refresh(); }

  refresh() {
    this.loading = true;
    this.error = '';
    forkJoin({
      report: this.api.agentReport(this.mode, this.days),
      decisions: this.api.agentDecisions(this.mode, this.days, this.limit, this.offset),
    }).subscribe({
      next: (result) => {
        this.report = result.report;
        this.decisions = result.decisions;
        this.loading = false;
      },
      error: () => {
        this.error = 'Could not load AI-agent analysis from the API.';
        this.loading = false;
      },
    });
  }

  page(direction: number) {
    this.offset = Math.max(0, this.offset + direction * this.limit);
    this.loading = true;
    this.api.agentDecisions(this.mode, this.days, this.limit, this.offset).subscribe({
      next: (result) => { this.decisions = result; this.error = ''; this.loading = false; },
      error: () => { this.error = 'Could not load AI-agent decisions from the API.'; this.loading = false; },
    });
  }

  fixed(value: number | null, digits: number): string {
    return value === null ? '-' : value.toFixed(digits);
  }

  percent(value: number | null): string {
    return value === null ? '-' : `${value.toFixed(1)}%`;
  }

  private metricRows(comparison: AgentComparison): MetricRow[] {
    return [
      { label: 'Agent', efficiency: comparison.agent_eff, range: comparison.agent_range_atr },
      { label: 'Fixed', efficiency: comparison.fixed_eff, range: comparison.fixed_range_atr },
      { label: 'Baseline', efficiency: comparison.base_eff, range: comparison.base_range_atr },
      { label: 'Any pair', efficiency: comparison.any_eff, range: comparison.any_range_atr },
    ];
  }
}
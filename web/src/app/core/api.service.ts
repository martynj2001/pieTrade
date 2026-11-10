import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Account, DrawdownResult, ExitReasons, Filters, GroupStat, HoldingTime, Meta, Summary, TradeDetail, TradePage,
  AtrBucket, AgentDecisionPage, AgentMode, AgentReport,
} from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  private params(f: Record<string, unknown>): HttpParams {
    let p = new HttpParams();
    for (const [k, v] of Object.entries(f)) {
      if (v !== null && v !== undefined && v !== '') p = p.set(k, String(v));
    }
    return p;
  }

  meta(): Observable<Meta> { return this.http.get<Meta>(`${this.base}/api/meta`); }

  trades(f: Filters, sort: string, order: 'asc' | 'desc', limit: number, offset: number): Observable<TradePage> {
    return this.http.get<TradePage>(`${this.base}/api/trades`, {
      params: this.params({ ...f, sort, order, limit, offset }),
    });
  }

  trade(id: string): Observable<TradeDetail> {
    return this.http.get<TradeDetail>(`${this.base}/api/trades/${encodeURIComponent(id)}`);
  }

  private analytics<T>(path: string, f: Filters, extra: Record<string, unknown> = {}): Observable<T> {
    return this.http.get<T>(`${this.base}/api/analytics/${path}`, { params: this.params({ ...f, ...extra }) });
  }

  summary(f: Filters) { return this.analytics<Summary>('summary', f); }
  byInstrument(f: Filters) { return this.analytics<GroupStat[]>('by-instrument', f); }
  bySession(f: Filters) { return this.analytics<GroupStat[]>('by-session', f); }
  byDirection(f: Filters) { return this.analytics<GroupStat[]>('by-direction', f); }
  holdingTime(f: Filters) { return this.analytics<HoldingTime>('holding-time', f); }
  atrRanges(f: Filters) { return this.analytics<AtrBucket[]>('atr-ranges', f); }
  exitReasons(f: Filters) { return this.analytics<ExitReasons>('exit-reasons', f); }
  drawdown(f: Filters, startingBalance?: number) {
    return this.analytics<DrawdownResult>('drawdown', f, { starting_balance: startingBalance });
  }

  agentReport(mode: AgentMode, days?: number): Observable<AgentReport> {
    return this.http.get<AgentReport>(`${this.base}/api/agent/report`, {
      params: this.params({ mode, days }),
    });
  }

  agentDecisions(mode: AgentMode, days: number | undefined, limit: number, offset: number) {
    return this.http.get<AgentDecisionPage>(`${this.base}/api/agent/decisions`, {
      params: this.params({ mode, days, limit, offset }),
    });
  }

  account() { return this.http.get<Account>(`${this.base}/api/account`); }

  outcomesReadme() {
    return this.http.get<{ markdown: string }>(`${this.base}/api/agent/outcomes-readme`);
  }
}

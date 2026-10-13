import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { Filters, TradePage } from '../core/models';
import { FilterBarComponent } from '../shared/filter-bar.component';

@Component({
  selector: 'app-trade-list',
  standalone: true,
  imports: [FilterBarComponent, RouterLink, DatePipe, DecimalPipe],
  template: `
    <h2>Trades</h2>
    <app-filter-bar (changed)="onFilters($event)" />
    @if (error) { <p class="err">{{ error }}</p> }
    <table>
      <thead><tr>
        @for (c of cols; track c.key) {
          <th (click)="sortBy(c.key)">{{ c.label }}{{ sort === c.key ? (order === 'asc' ? ' ▲' : ' ▼') : '' }}</th>
        }
      </tr></thead>
      <tbody>
        @for (t of page?.items ?? []; track t.trade_id) {
          <tr>
            <td><a [routerLink]="['/trades', t.trade_id]">{{ t.trade_id }}</a></td>
            <td>{{ t.instrument }}</td>
            <td>{{ t.direction }}</td>
            <td>{{ t.session }}</td>
            <td>{{ t.entry_time | date: 'yyyy-MM-dd HH:mm' }}</td>
            <td>{{ t.exit_time | date: 'yyyy-MM-dd HH:mm' }}</td>
            <td>{{ t.entry_price }}</td>
            <td>{{ t.exit_price }}</td>
            <td>{{ t.status }}</td>
            <td [class.pos]="(t.pnl_currency ?? 0) > 0" [class.neg]="(t.pnl_currency ?? 0) < 0">
              {{ t.pnl_currency | number: '1.2-4' }}</td>
            <td>{{ t.pnl_pips | number: '1.1-1' }}</td>
            <td>{{ t.duration_minutes }}</td>
          </tr>
        } @empty { <tr><td colspan="12">No trades.</td></tr> }
      </tbody>
    </table>
    <div class="pager">
      <button (click)="go(-1)" [disabled]="offset === 0">Prev</button>
      <span>{{ page ? offset + 1 : 0 }}–{{ offset + (page?.items?.length ?? 0) }} of {{ page?.total ?? 0 }}</span>
      <button (click)="go(1)" [disabled]="!page || offset + limit >= page.total">Next</button>
    </div>`,
  styles: [`
    table { border-collapse: collapse; width: 100%; font-size: .9rem; }
    th, td { padding: .4rem .6rem; border-bottom: 1px solid #ddd; text-align: left; }
    th { cursor: pointer; background: #f4f4f4; white-space: nowrap; }
    .pos { color: #0a7d2c; } .neg { color: #c0392b; } .err { color: #c0392b; }
    .pager { display: flex; gap: 1rem; align-items: center; margin-top: 1rem; }`],
})
export class TradeListComponent {
  private api = inject(ApiService);
  page?: TradePage;
  error = '';
  filters: Filters = {};
  sort = 'entry_time';
  order: 'asc' | 'desc' = 'desc';
  limit = 25;
  offset = 0;
  cols = [
    { key: 'trade_id', label: 'ID' }, { key: 'instrument', label: 'Pair' },
    { key: 'direction', label: 'Dir' }, { key: 'session', label: 'Session' },
    { key: 'entry_time', label: 'Entry' }, { key: 'exit_time', label: 'Exit' },
    { key: 'entry_price', label: 'Entry px' }, { key: 'exit_price', label: 'Exit px' },
    { key: 'status', label: 'Status' }, { key: 'pnl_currency', label: 'P&L' },
    { key: 'pnl_pips', label: 'Pips' }, { key: 'duration_minutes', label: 'Mins' },
  ];

  onFilters(f: Filters) { this.filters = f; this.offset = 0; this.load(); }

  sortBy(key: string) {
    this.order = this.sort === key && this.order === 'desc' ? 'asc' : 'desc';
    this.sort = key;
    this.load();
  }

  go(dir: number) { this.offset = Math.max(0, this.offset + dir * this.limit); this.load(); }

  load() {
    this.api.trades(this.filters, this.sort, this.order, this.limit, this.offset).subscribe({
      next: (p) => { this.page = p; this.error = ''; },
      error: () => (this.error = 'Could not load trades from the API.'),
    });
  }
}

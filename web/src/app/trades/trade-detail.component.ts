import { DatePipe, JsonPipe, KeyValuePipe } from '@angular/common';
import { Component, OnInit, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { TradeDetail } from '../core/models';

@Component({
  selector: 'app-trade-detail',
  standalone: true,
  imports: [RouterLink, DatePipe, KeyValuePipe, JsonPipe],
  template: `
    <a routerLink="/trades">← Trades</a>
    @if (error) { <p class="err">{{ error }}</p> }
    @if (detail; as d) {
      <h2>Trade {{ d.trade.trade_id }} — {{ d.trade.instrument }} {{ d.trade.direction }}</h2>
      <dl>
        @for (kv of d.trade | keyvalue; track kv.key) { <dt>{{ kv.key }}</dt><dd>{{ kv.value ?? '—' }}</dd> }
      </dl>
      <h3>Signals</h3>
      @for (s of d.signals; track s.id) { <pre>{{ s | json }}</pre> }
      @empty { <p>No signal data recorded for this trade.</p> }
      <h3>Events</h3>
      <ul>
        @for (e of d.events; track e.id) {
          <li>{{ e.event_time | date: 'yyyy-MM-dd HH:mm:ss' }} — <b>{{ e.event_type }}</b>: {{ e.message }}</li>
        } @empty { <li>No events.</li> }
      </ul>
    }`,
  styles: [`
    dl { display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1rem; }
    dt { color: #666; } dd { margin: 0; } pre { background: #f4f4f4; padding: .5rem; overflow: auto; }
    .err { color: #c0392b; }`],
})
export class TradeDetailComponent implements OnInit {
  private api = inject(ApiService);
  id = input.required<string>();
  detail?: TradeDetail;
  error = '';

  ngOnInit() {
    this.api.trade(this.id()).subscribe({
      next: (d) => (this.detail = d),
      error: () => (this.error = 'Trade not found or API unavailable.'),
    });
  }
}

import { DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap, timer } from 'rxjs';
import { ApiService } from '../core/api.service';
import { Account } from '../core/models';

@Component({
  selector: 'app-account-summary',
  standalone: true,
  imports: [DecimalPipe],
  template: `
    <section class="summary">
      <h3>Account Summary</h3>
      @if (unavailable) { <p class="unavailable">Account Unavailable</p> }
      @if (account; as data) {
        <div class="cards">
          <div class="card"><span>Balance</span><b>£{{ data.balance | number: '1.2-2' }}</b></div>
          <div class="card"><span>NAV</span><b>£{{ data.NAV | number: '1.2-2' }}</b></div>
          <div class="card"><span>Unrealised P/L</span><b [class.pos]="data.unrealizedPL > 0" [class.neg]="data.unrealizedPL < 0">£{{ data.unrealizedPL | number: '1.2-2' }}</b></div>
          <div class="card"><span>Realised P/L</span><b [class.pos]="data.pl > 0" [class.neg]="data.pl < 0">£{{ data.pl | number: '1.2-2' }}</b></div>
          <div class="card"><span>Open Positions</span><b>{{ data.openPositionCount }}</b></div>
          <div class="card"><span>Open Trades</span><b>{{ data.openTradeCount }}</b></div>
        </div>
      }
    </section>`,
  styles: [`
    .summary { margin-bottom: 1.5rem; }
    h3 { margin: 0 0 .75rem; font-size: 1rem; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .75rem; }
    .card { min-width: 0; background: #f4f6f8; border-radius: 8px; padding: .75rem; display: flex; flex-direction: column; }
    .card span { font-size: .75rem; color: #666; }
    .card b { font-size: 1.15rem; overflow-wrap: anywhere; }
    .pos { color: #16a34a; } .neg { color: #dc2626; }
    .unavailable { color: #c0392b; }
  `],
})
export class AccountSummaryComponent {
  private api = inject(ApiService);
  account: Account | null = null;
  unavailable = false;

  constructor() {
    timer(0, 30_000).pipe(
      switchMap(() => this.api.account().pipe(catchError(() => of(null)))),
      takeUntilDestroyed(),
    ).subscribe((account) => {
      this.account = account;
      this.unavailable = account === null;
    });
  }
}

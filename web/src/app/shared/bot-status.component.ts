import { Component, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { catchError, of, switchMap, timer } from 'rxjs';
import { ApiService } from '../core/api.service';
import { BotStatus } from '../core/models';

@Component({
  selector: 'app-bot-status',
  standalone: true,
  template: `
    <section class="status-card">
      <h3>Bot Status</h3>
      <div class="pill" [class]="statusClass" role="status">
        <span class="dot"></span>{{ label }}
      </div>
      @if (status; as data) {
        <div class="details">
          @if (data.age_seconds != null) { <span>Last Heartbeat {{ heartbeatAge }} Ago</span> }
          @if (data.uptime_seconds != null) { <span>Uptime {{ uptime }}</span> }
          @if (data.state === 'trading' && data.instrument) { <span>Trading {{ data.instrument.replace('_', '/') }}</span> }
          @if (data.state === 'markets_closed') { <span>Markets Closed</span> }
          @if (data.last_signal_check) { <span>Last Signal Check {{ signalTime(data.last_signal_check) }} UTC</span> }
        </div>
      }
    </section>`,
  styles: [`
    .status-card { background: #f4f6f8; border-radius: 8px; padding: .75rem; margin-bottom: 1.5rem; }
    h3 { margin: 0 0 .75rem; font-size: 1rem; }
    .pill { --status-color: #6b7280; display: inline-flex; align-items: center; gap: .45rem; color: var(--status-color); font-weight: 600; }
    .running { --status-color: #16a34a; } .delayed { --status-color: #f59e0b; }
    .offline, .unreachable { --status-color: #dc2626; }
    .dot { width: .55rem; height: .55rem; border-radius: 50%; background: var(--status-color); flex: none; }
    .running .dot { animation: pulse 2s infinite; }
    .details { display: flex; flex-wrap: wrap; gap: .25rem .5rem; margin-top: .5rem; font-size: .8rem; color: #666; }
    .details span + span::before { content: '·'; margin-right: .5rem; }
    @keyframes pulse { 50% { opacity: .4; } }
    @media (prefers-reduced-motion: reduce) { .running .dot { animation: none; } }
  `],
})
export class BotStatusComponent {
  private api = inject(ApiService);
  private receivedAt = Date.now();
  private now = Date.now();
  status: BotStatus | null = { status: 'unknown' };
  unreachable = false;

  constructor() {
    timer(0, 10_000).pipe(
      switchMap(() => this.api.botStatus().pipe(catchError(() => of(null)))),
      takeUntilDestroyed(),
    ).subscribe((status) => {
      this.receivedAt = this.now = Date.now();
      this.status = status;
      this.unreachable = status === null;
    });
    timer(0, 1_000).pipe(takeUntilDestroyed()).subscribe(() => this.now = Date.now());
  }

  get statusClass(): string { return this.unreachable ? 'unreachable' : this.status?.status ?? 'unknown'; }
  get label(): string {
    if (this.unreachable) return 'API Unreachable';
    return { running: 'Bot Running', delayed: 'Bot Delayed', offline: 'Bot Offline',
      stopped: 'Bot Stopped', unknown: 'Status Unknown' }[this.status?.status ?? 'unknown'];
  }
  get heartbeatAge(): string {
    const seconds = Math.floor((this.status?.age_seconds ?? 0) + (this.now - this.receivedAt) / 1000);
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m`;
  }
  get uptime(): string {
    const minutes = Math.floor(((this.status?.uptime_seconds ?? 0) + (this.now - this.receivedAt) / 1000) / 60);
    return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;
  }
  signalTime(timestamp: string): string {
    const date = new Date(timestamp);
    return `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}`;
  }
}
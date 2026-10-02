import { Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';
import { Filters, Meta } from '../core/models';

@Component({
  selector: 'app-filter-bar',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="bar">
      @for (f of fields; track f.key) {
        <label>{{ f.label }}
          <select [(ngModel)]="filters[f.key]" (ngModelChange)="emit()">
            <option value="">All</option>
            @for (o of meta?.[f.meta] ?? []; track o) { <option [value]="o">{{ o }}</option> }
          </select>
        </label>
      }
      <label>From <input type="date" [(ngModel)]="filters.date_from" (ngModelChange)="emit()" /></label>
      <label>To <input type="date" [(ngModel)]="filters.date_to" (ngModelChange)="emit()" /></label>
      <button type="button" (click)="reset()">Reset</button>
    </div>`,
  styles: [`
    .bar { display: flex; flex-wrap: wrap; gap: .75rem; align-items: end; margin-bottom: 1rem; }
    label { display: flex; flex-direction: column; font-size: .8rem; color: #555; gap: .2rem; }
    select, input, button { padding: .35rem .5rem; }`],
})
export class FilterBarComponent implements OnInit {
  private api = inject(ApiService);
  @Output() changed = new EventEmitter<Filters>();
  meta?: Meta;
  filters: Filters = {};
  fields: { key: keyof Filters; meta: keyof Meta; label: string }[] = [
    { key: 'instrument', meta: 'instrument', label: 'Pair' },
    { key: 'strategy', meta: 'strategy', label: 'Strategy' },
    { key: 'direction', meta: 'direction', label: 'Direction' },
    { key: 'session', meta: 'session', label: 'Session' },
  ];

  ngOnInit() {
    this.api.meta().subscribe((m) => (this.meta = m));
    this.emit();
  }

  emit() {
    const f: Filters = { ...this.filters };
    if (f.date_to) f.date_to = `${f.date_to}T23:59:59`;
    this.changed.emit(f);
  }

  reset() { this.filters = {}; this.emit(); }
}

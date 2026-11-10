import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { marked } from 'marked';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-agent-outcomes',
  standalone: true,
  imports: [RouterLink],
  template: `
    <a routerLink="/agent">← Agent</a>
    <h2>Agent Outcomes Guide</h2>
    @if (loading) { <p>Loading Outcomes Guide…</p> }
    @if (error) { <p class="err">{{ error }}</p> }
    <article class="md" [innerHTML]="html"></article>`,
})
export class AgentOutcomesComponent {
  private api = inject(ApiService);
  html = '';
  loading = true;
  error = '';

  constructor() {
    this.api.outcomesReadme().subscribe({
      next: ({ markdown }) => {
        const document = new DOMParser().parseFromString(marked.parse(markdown, { async: false }), 'text/html');
        document.querySelectorAll('table').forEach((table) => {
          const wrapper = document.createElement('div');
          wrapper.className = 'table-wrap';
          table.replaceWith(wrapper);
          wrapper.append(table);
        });
        this.html = document.body.innerHTML;
        this.loading = false;
      },
      error: () => {
        this.error = 'Could not load the outcomes guide from the API.';
        this.loading = false;
      },
    });
  }
}

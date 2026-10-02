import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <strong>pyTrade</strong>
      <nav>
        <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a>
        <a routerLink="/trades" routerLinkActive="active">Trades</a>
      </nav>
    </header>
    <main><router-outlet /></main>`,
  styles: [`
    header { display: flex; gap: 2rem; align-items: center; padding: .75rem 1.5rem; background: #1f2937; color: #fff; }
    nav { display: flex; gap: 1rem; } nav a { color: #cbd5e1; text-decoration: none; }
    nav a.active { color: #fff; border-bottom: 2px solid #3b82f6; }
    main { padding: 1.5rem; }`],
})
export class AppComponent {}

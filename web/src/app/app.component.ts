import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <header>
      <img class="logo" src="/images/logo_gui.png" alt="pyTrade">
      <nav>
        <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a>
        <a routerLink="/trades" routerLinkActive="active">Trades</a>
      </nav>
    </header>
    <main><router-outlet /></main>`,
  styles: [`
    header { display: flex; gap: 2rem; align-items: center; padding: .375rem 1.5rem; background: #1f2937; color: #fff; }
    .logo { display: block; width: 142px; height: 41px; object-fit: contain; }
    nav { display: flex; gap: 1rem; } nav a { color: #cbd5e1; text-decoration: none; }
    nav a.active { color: #fff; border-bottom: 2px solid #3b82f6; }
    main { position: relative; isolation: isolate; padding: 1.5rem; }
    main::before { content: ''; position: absolute; inset: 0; z-index: -1; background: url('/images/Icon_mstr.png') center / min(354px, 60vw) auto no-repeat; opacity: .12; }`],
})
export class AppComponent {}

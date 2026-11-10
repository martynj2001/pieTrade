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
        <a routerLink="/agent" routerLinkActive="active">Agent</a>
        <a routerLink="/trades" routerLinkActive="active">Trades</a>
      </nav>
    </header>
    <main><router-outlet /></main>`,
  styles: [`
    header { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; padding: max(.375rem, env(safe-area-inset-top)) 1.5rem .375rem; background: #1f2937; color: #fff; }
    .logo { display: block; width: 142px; height: 41px; object-fit: contain; }
    nav { display: flex; flex-wrap: wrap; gap: .25rem; } nav a { display: flex; align-items: center; min-height: 44px; padding: .75rem .5rem; color: #cbd5e1; text-decoration: none; }
    nav a.active { color: #fff; border-bottom: 2px solid #3b82f6; }
    main { position: relative; isolation: isolate; }
    main::before { content: ''; position: absolute; inset: 0; z-index: -1; background: url('/images/Icon_mstr.png') center / min(354px, 60vw) auto no-repeat; opacity: .12; }`],
})
export class AppComponent {}

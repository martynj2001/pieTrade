import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: 'dashboard', loadComponent: () => import('./dashboard/dashboard.component').then((m) => m.DashboardComponent) },
  { path: 'agent', loadComponent: () => import('./agent/agent.component').then((m) => m.AgentComponent) },
  { path: 'trades', loadComponent: () => import('./trades/trade-list.component').then((m) => m.TradeListComponent) },
  { path: 'trades/:id', loadComponent: () => import('./trades/trade-detail.component').then((m) => m.TradeDetailComponent) },
  // Future modules: optimisation, backtests
];

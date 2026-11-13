export interface Filters {
  instrument?: string; strategy?: string; status?: string; direction?: string;
  session?: string; date_from?: string; date_to?: string;
}
export interface Meta {
  instrument: string[]; strategy: string[]; status: string[]; direction: string[]; session: string[];
}
export interface Trade {
  id: number; trade_id: string; instrument: string; direction: string; strategy: string;
  entry_time: string; exit_time: string | null; entry_price: number; exit_price: number | null;
  stop_loss: number; take_profit: number; units: number; risk_amount: number; status: string;
  close_reason: string | null; pnl_currency: number | null; pnl_pips: number | null;
  duration_minutes: number | null; session: string; created_at: string;
}
export interface TradePage { total: number; limit: number; offset: number; items: Trade[]; }
export interface Signal {
  id: number; trade_id: string; ema20: number | null; ema50: number | null; atr14: number | null;
  adx: number | null; trend_strength: number | null; rejection_candle: number | null;
  pullback_detected: number | null; close_price: number | null; high_price: number | null;
  low_price: number | null; signal_timestamp: string | null;
}
export interface TradeEvent { id: number; trade_id: string; event_time: string; event_type: string; message: string; }
export interface TradeDetail { trade: Trade; signals: Signal[]; events: TradeEvent[]; }
export interface Summary {
  trades: number; wins: number; losses: number; win_rate: number | null; total_pnl: number;
  avg_pnl: number | null; profit_factor: number | null; gross_profit: number; gross_loss: number;
  avg_trades_per_day: number | null;
}
export interface GroupStat extends Omit<Summary, 'gross_profit' | 'gross_loss'> { [key: string]: string | number | null; }
export interface HoldingTime { overall: { trades: number; avg_minutes: number | null; median_minutes: number | null }; }
export interface AtrBucket extends Omit<Summary, 'gross_profit' | 'gross_loss'> { atr_min: number; atr_max: number; }
export interface ExitReasons {
  trades: number;
  take_profit: { count: number; pct: number | null };
  stop_loss: { count: number; pct: number | null };
  other: { count: number; pct: number | null };
}
export interface DrawdownResult {
  max_drawdown: number; max_drawdown_pct: number | null; peak_time: string | null; trough_time: string | null;
  curve: { time: string; trade_id: string; equity: number; drawdown: number }[];
}

export type AgentMode = 'all' | 'shadow' | 'live';

export interface AgentComparison {
  n: number;
  agent_eff: number | null; fixed_eff: number | null; base_eff: number | null; any_eff: number | null;
  agent_range_atr: number | null; fixed_range_atr: number | null;
  base_range_atr: number | null; any_range_atr: number | null;
  pct_beats_fixed_eff: number | null; pct_beats_base_eff: number | null;
  pct_beats_fixed_range: number | null; pct_beats_base_range: number | null;
}

export interface AgentReliability {
  total: number; ok_pct: number | null; avg_latency_s: number | null;
  by_status: { status: string; count: number }[];
}

export interface AgentReportAvailable {
  available: true; message: null; filters: { mode: AgentMode; days: number | null };
  reliability: AgentReliability;
  agreement: { n: number; pct_same_as_fixed: number | null; pct_same_as_baseline: number | null };
  comparison: AgentComparison; disagreements: AgentComparison;
  by_market: (AgentComparison & { market: string })[];
  news_cost: {
    decisions_with_news_exclusion: number; input_tokens: number;
    output_tokens: number; est_cost_usd: number; est_cost_gbp: number;
  };
  live_pnl: { market: string | null; trades: number; pnl: number | null; win_pct: number | null }[];
  go_live: { ready: boolean; checks: { name: string; passed: boolean; value: string; target: string }[] };
}

export interface AgentReportUnavailable { available: false; message: string; }
export type AgentReport = AgentReportAvailable | AgentReportUnavailable;

export interface AgentDecision {
  id: number; target_hour: string; mode: AgentMode; status: string; market: string | null;
  instrument: string | null; fixed_instrument: string | null; baseline_instrument: string | null;
  reason: string | null; latency_s: number | null; error: string | null;
}

export interface AgentDecisionPage {
  total: number; limit: number; offset: number; items: AgentDecision[];
}

export interface Account {
  balance: number; NAV: number; unrealizedPL: number; pl: number;
  marginAvailable: number; marginUsed: number; openPositionCount: number; openTradeCount: number;
}

export interface BotStatus {
  status: 'running' | 'delayed' | 'offline' | 'stopped' | 'unknown';
  state?: string; age_seconds?: number; uptime_seconds?: number | null;
  market?: string | null; instrument?: string | null; last_signal_check?: string | null; updated_at?: string;
}

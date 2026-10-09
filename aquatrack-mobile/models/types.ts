export type Household = { id: number; name: string; address: string };
export type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type UsageSummary = { id: number; period_type: string; period_start: string; total_consumption: number; total_cubic_meters: number };
export type Reading = { id: number; timestamp: string; flow_rate: number; pressure_level: number | null; is_anomalous: boolean };
export type Leak = {
  id: number; detected_at: string; resolved_at: string | null; status: string; stage: number;
  classification: string; duration_hours: number; avg_flow_rate: number; avg_pressure: number | null;
  recommended_steps: { urgency: string; message: string; checklist: { priority: number; item: string; how: string }[] } | null;
};
export type Alert = { id: number; alert_type: string; severity: string; message: string; sent_at: string; is_read: boolean };
export type Forecast = {
  forecast_month: string; consumed_to_date: number; predicted_consumption: number; predicted_bill: number;
  average_flow_rate: number; method: string; cost_per_cubic_meter: number | null; schedule: string;
  breakdown: { label: string; cubic_meters: number; rate: number | null; amount: number }[];
};
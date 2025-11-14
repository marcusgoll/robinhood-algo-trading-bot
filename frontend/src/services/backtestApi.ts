/**
 * API client for backtest endpoints with automatic retries.
 *
 * Handles:
 * - GET /api/v1/backtests (list with filtering)
 * - GET /api/v1/backtests/:id (detail view)
 * - Automatic retry on network errors (3 attempts)
 * - Error normalization
 */

import type { BacktestListResponse, BacktestDetail } from '../types/backtest';

const API_BASE = '/api/v1/backtests';
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

/**
 * Sleep helper for retry delays.
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Generic fetch with retry logic.
 */
async function fetchWithRetry<T>(
  url: string,
  options: RequestInit = {},
  retries = MAX_RETRIES
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      // Don't retry 4xx errors (except 429)
      if (response.status >= 400 && response.status < 500 && response.status !== 429) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    if (retries > 0) {
      console.warn(`Request failed, retrying... (${MAX_RETRIES - retries + 1}/${MAX_RETRIES})`, error);
      await sleep(RETRY_DELAY_MS);
      return fetchWithRetry<T>(url, options, retries - 1);
    }

    throw error;
  }
}

export interface ListBacktestsParams {
  strategy?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}

/**
 * List all backtests with optional filtering.
 *
 * @param params - Filter parameters
 * @returns List response with summaries
 */
export async function listBacktests(
  params: ListBacktestsParams = {}
): Promise<BacktestListResponse> {
  const searchParams = new URLSearchParams();

  if (params.strategy) searchParams.set('strategy', params.strategy);
  if (params.start_date) searchParams.set('start_date', params.start_date);
  if (params.end_date) searchParams.set('end_date', params.end_date);
  if (params.limit) searchParams.set('limit', String(params.limit));

  const url = searchParams.toString()
    ? `${API_BASE}?${searchParams}`
    : API_BASE;

  return fetchWithRetry<BacktestListResponse>(url);
}

/**
 * Get full backtest details by ID.
 *
 * @param backtestId - Backtest identifier
 * @returns Complete backtest detail
 * @throws Error if backtest not found (404)
 */
export async function getBacktestDetail(backtestId: string): Promise<BacktestDetail> {
  return fetchWithRetry<BacktestDetail>(`${API_BASE}/${backtestId}`);
}

/**
 * Get unique strategy names from backtest list.
 *
 * Helper function for filter dropdowns.
 */
export async function getStrategies(): Promise<string[]> {
  const response = await listBacktests();
  const strategies = new Set(response.data.map(bt => bt.strategy));
  return Array.from(strategies).sort();
}

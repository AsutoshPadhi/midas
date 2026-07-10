import { api } from './api';
import { APP_CONFIG } from '../constants/config';
import type { Transaction } from '../types/transaction';

async function sync(query = 'in:inbox', maxResults = 50): Promise<Transaction[]> {
  const { data } = await api.get<Transaction[] | { transactions: Transaction[] }>(
    '/api/v1/email/transactions/sync',
    {
      baseURL: APP_CONFIG.backendApiUrl,
      params: { query, max_results: maxResults },
    }
  );
  return Array.isArray(data) ? data : data.transactions;
}

export const transactionsService = { sync };

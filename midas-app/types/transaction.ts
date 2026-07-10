export type Transaction = {
  id: string;
  merchant?: string;
  counterparty?: string;
  name?: string;
  description?: string;
  subject?: string;
  amount: number;
  currency?: string;
  category?: string;
  direction?: 'debit' | 'credit';
  date?: string;
  created_at?: string;
  txn_timestamp?: string;
};

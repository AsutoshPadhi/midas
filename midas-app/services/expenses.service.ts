import { api } from './api';
import type { Expense, ExpenseInput } from '../types/expense';

async function list() {
  const { data } = await api.get<Expense[]>('/expenses');
  return data;
}

async function create(payload: ExpenseInput) {
  const { data } = await api.post<Expense>('/expenses', payload);
  return data;
}

export const expensesService = {
  list,
  create,
};

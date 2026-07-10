import { useQuery } from '@tanstack/react-query';
import { expensesService } from '../services/expenses.service';

export function useExpenses() {
  return useQuery({
    queryKey: ['expenses'],
    queryFn: expensesService.list,
  });
}

export type Expense = {
  id: string;
  title: string;
  amount: number;
  category: string;
  createdAt: string;
};

export type ExpenseInput = {
  title: string;
  amount: number;
  category: string;
};

import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View, Pressable } from 'react-native';
import { PieChart } from '../../components/PieChart';
import type { PieSlice } from '../../components/PieChart';
import { APP_CONFIG } from '../../constants/config';
import { transactionsService } from '../../services/transactions.service';
import { useAuthStore } from '../../store/auth.store';
import type { Transaction } from '../../types/transaction';

const CHART_COLORS = [
  '#1B5E3A', '#2E7D52', '#43A06B', '#68B585', '#8FCCA3',
  '#D4A017', '#2980B9', '#8E44AD', '#C0392B', '#E67E22',
];

function groupByCategory(transactions: Transaction[]): PieSlice[] {
  const map: Record<string, number> = {};
  for (const t of transactions) {
    // Only include debits
    if (t.direction !== 'debit') continue;
    const cat = t.category ?? 'Other';
    map[cat] = (map[cat] ?? 0) + t.amount;
  }
  return Object.entries(map)
    .sort(([, a], [, b]) => b - a)
    .map(([label, value], i) => ({
      label,
      value,
      color: CHART_COLORS[i % CHART_COLORS.length],
    }));
}

export default function HomeScreen() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<{ label: string; value: number } | null>(null);
  const setStoreTransactions = useAuthStore((state) => state.setTransactions);

  useEffect(() => {
    transactionsService
      .sync()
      .then((data) => {
        console.log('[home] transactions:', data);
        if (data.length > 0) {
          console.log('[home] first transaction keys:', Object.keys(data[0]));
        }
        setTransactions(data);
        setStoreTransactions(data);
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof Error ? err.message : JSON.stringify(err);
        setError(msg);
      })
      .finally(() => setLoading(false));
  }, [setStoreTransactions]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#1B5E3A" />
        <Text style={styles.loadingText}>Syncing transactions...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Error: {error}</Text>
      </View>
    );
  }

  if (transactions.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>No transactions found.</Text>
      </View>
    );
  }

  const debits = transactions.filter((t) => t.direction === 'debit');
  if (debits.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>No debits found.</Text>
      </View>
    );
  }

  const slices = groupByCategory(transactions);
  const total = debits.reduce((sum, t) => sum + t.amount, 0);
  const currentMonth = new Date().toLocaleString('default', { month: 'long' });

  // Get transactions for selected category
  const categoryTransactions = selectedCategory
    ? debits.filter((t) => (t.category ?? 'Other') === selectedCategory.label)
    : [];

  return (
    <Pressable onPress={() => setSelectedCategory(null)} style={{ flex: 1 }}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        scrollEnabled={true}
      >
        <Text style={styles.heading}>Spending Overview for {currentMonth}</Text>

        <Pressable 
          onPress={(e) => e.stopPropagation()}
          style={styles.chartWrap}
        >
          <PieChart
            slices={slices}
            size={220}
            onSlicePress={(label, value) => setSelectedCategory({ label, value })}
            selectedSlice={selectedCategory?.label}
          />
        </Pressable>

        {!selectedCategory && (
          <View style={styles.selectedCategoryCard}>
            <Text style={styles.selectedCategoryLabel}>Total Spend</Text>
            <Text style={styles.selectedCategoryAmount}>
              {APP_CONFIG.currency}{total.toFixed(2)}
            </Text>
          </View>
        )}

        {selectedCategory && (
          <Pressable onPress={(e) => e.stopPropagation()}>
            <View style={styles.selectedCategoryCard}>
              <Text style={styles.selectedCategoryLabel}>{selectedCategory.label}</Text>
              <Text style={styles.selectedCategoryAmount}>
                {APP_CONFIG.currency}{selectedCategory.value.toFixed(2)}
              </Text>
            </View>
          </Pressable>
        )}

        {selectedCategory && (
          <Pressable onPress={(e) => e.stopPropagation()}>
            <View style={styles.categoryTransactionsContainer}>
              <View style={styles.transactionsTable}>
                <View style={styles.tableHeader}>
                  <Text style={[styles.tableHeaderCell, { flex: 1.5 }]}>Merchant</Text>
                  <Text style={[styles.tableHeaderCell, { flex: 0.8 }]}>Amount</Text>
                  <Text style={[styles.tableHeaderCell, { flex: 0.7 }]}>Date</Text>
                </View>
                {categoryTransactions.length === 0 ? (
                  <Text style={styles.emptyTransactions}>No transactions found</Text>
                ) : (
                  categoryTransactions.map((t, i) => {
                    const dateStr = t.txn_timestamp ?? t.date ?? t.created_at ?? '';
                    const date = new Date(dateStr);
                    const day = date.getDate();
                    const ordinalDay = day + (day % 10 === 1 && day !== 11 ? 'st' : day % 10 === 2 && day !== 12 ? 'nd' : day % 10 === 3 && day !== 13 ? 'rd' : 'th');
                    return (
                      <View key={i} style={[styles.tableRow, { backgroundColor: '#FADBD8' }]}>
                        <Text style={[styles.tableCell, { flex: 1.5 }]}>{t.counterparty ?? t.merchant ?? '-'}</Text>
                        <Text style={[styles.tableCell, { flex: 0.8 }]}>{APP_CONFIG.currency}{t.amount.toFixed(2)}</Text>
                        <Text style={[styles.tableCell, { flex: 0.7 }]}>{ordinalDay}</Text>
                      </View>
                    );
                  })
                )}
              </View>
            </View>
          </Pressable>
        )}

        {!selectedCategory && (
          <View style={styles.legend}>
            {slices.map((s) => (
              <View key={s.label} style={styles.legendRow}>
                <View style={[styles.legendDot, { backgroundColor: s.color }]} />
                <Text style={styles.legendLabel}>{s.label}</Text>
                <Text style={styles.legendValue}>{APP_CONFIG.currency}{s.value.toFixed(2)}</Text>
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#F7F5F0' },
  content: { padding: 24, paddingBottom: 48 },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: '#F7F5F0',
  },
  heading: { fontSize: 22, fontWeight: '700', color: '#1B5E3A', marginBottom: 40 },
  subheading: { fontSize: 14, color: '#2E3F34', marginTop: 4, marginBottom: 28 },
  chartWrap: { width: 220, height: 220, borderRadius: 110, alignItems: 'center', justifyContent: 'center', marginBottom: 32, alignSelf: 'center' },
  selectedCategoryCard: {
    backgroundColor: '#1B5E3A',
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 20,
    marginBottom: 24,
    alignItems: 'center',
  },
  selectedCategoryLabel: {
    fontSize: 14,
    color: '#F7F5F0',
    opacity: 0.8,
    marginBottom: 4,
  },
  selectedCategoryAmount: {
    fontSize: 28,
    fontWeight: '700',
    color: '#F7F5F0',
  },
  legend: { gap: 14 },
  legendRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  legendDot: { width: 14, height: 14, borderRadius: 7 },
  legendLabel: { flex: 1, fontSize: 15, color: '#2E3F34' },
  legendValue: { fontSize: 15, fontWeight: '600', color: '#1B5E3A' },
  loadingText: { fontSize: 15, color: '#2E3F34' },
  errorText: { fontSize: 15, color: '#C0392B' },
  emptyText: { fontSize: 15, color: '#2E3F34' },
  categoryTransactionsContainer: { marginBottom: 24 },
  transactionsTable: { borderRadius: 8, overflow: 'hidden' },
  tableHeader: { flexDirection: 'row', backgroundColor: '#1B5E3A', paddingVertical: 10, paddingHorizontal: 12 },
  tableHeaderCell: { fontSize: 12, fontWeight: '600', color: '#F7F5F0' },
  tableRow: { flexDirection: 'row', paddingVertical: 10, paddingHorizontal: 12, borderBottomWidth: 1, borderBottomColor: '#E8E8E8' },
  tableCell: { fontSize: 13, color: '#2E3F34' },
  emptyTransactions: { fontSize: 14, color: '#2E3F34', textAlign: 'center', paddingVertical: 16 },
});

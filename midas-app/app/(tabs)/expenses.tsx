import { StyleSheet, ScrollView, Text, View } from 'react-native';
import { APP_CONFIG } from '../../constants/config';
import { useAuthStore } from '../../store/auth.store';

function getOrdinalDay(dateStr?: string): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  const day = date.getDate();
  const suffix = day % 10 === 1 && day !== 11 ? 'st' : day % 10 === 2 && day !== 12 ? 'nd' : day % 10 === 3 && day !== 13 ? 'rd' : 'th';
  return `${day}${suffix}`;
}

export default function ExpensesScreen() {
  const transactions = useAuthStore((state) => state.transactions);

  if (transactions.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>No transactions found.</Text>
      </View>
    );
  }

  // Sort by date descending
  const sorted = [...transactions].sort((a, b) => {
    const dateA = new Date(a.txn_timestamp || a.date || a.created_at || 0).getTime();
    const dateB = new Date(b.txn_timestamp || b.date || b.created_at || 0).getTime();
    return dateB - dateA;
  });

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
      <Text style={styles.heading}>
        Transactions of {new Date().toLocaleString('default', { month: 'long' })}
      </Text>
      <View style={styles.tableHeader}>
        <Text style={[styles.cell, styles.headerCell, { flex: 1.5 }]}>Merchant</Text>
        <Text style={[styles.cell, styles.headerCell, { flex: 0.8 }]}>Amount</Text>
        <Text style={[styles.cell, styles.headerCell, { flex: 1.2 }]}>Category</Text>
        <Text style={[styles.cell, styles.headerCell, { flex: 0.6 }]}>Date</Text>
      </View>

      {sorted.map((t, i) => (
        <View
          key={t.id || i}
          style={[
            styles.tableRow,
            t.direction === 'debit' ? styles.debitRow : styles.creditRow,
          ]}
        >
          <Text style={[styles.cell, { flex: 1.5 }]} numberOfLines={2}>
            {t.counterparty || t.merchant || '-'}
          </Text>
          <Text style={[styles.cell, { flex: 0.8, fontWeight: '600' }]} numberOfLines={1}>
            {APP_CONFIG.currency}{Math.abs(t.amount).toFixed(0)}
          </Text>
          <Text style={[styles.cell, { flex: 1.2 }]} numberOfLines={1}>
            {t.category || '-'}
          </Text>
          <Text style={[styles.cell, { flex: 0.6 }]} numberOfLines={1}>
            {getOrdinalDay(t.txn_timestamp || t.date || t.created_at)}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1, backgroundColor: '#F7F5F0' },
  content: { padding: 12, paddingBottom: 48 },
  heading: { fontSize: 22, fontWeight: '700', color: '#1B5E3A', marginBottom: 16 },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    backgroundColor: '#F7F5F0',
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#1B5E3A',
    paddingVertical: 12,
    paddingHorizontal: 8,
    marginBottom: 4,
    borderRadius: 4,
  },
  headerCell: {
    color: '#F7F5F0',
    fontWeight: '700',
    fontSize: 12,
  },
  tableRow: {
    flexDirection: 'row',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E8E5DB',
  },
  debitRow: {
    backgroundColor: '#FADBD8',
  },
  creditRow: {
    backgroundColor: '#D5F4E6',
  },
  cell: {
    fontSize: 13,
    color: '#2E3F34',
  },
  emptyText: { fontSize: 15, color: '#2E3F34' },
});

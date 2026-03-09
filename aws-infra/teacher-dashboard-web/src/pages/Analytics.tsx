import { useCallback, useState } from 'react';
import { GlassCard } from '../components/dashboard/GlassCard';
import { AnalyticsFilters } from '../components/analytics/AnalyticsFilters';
import { GraphPlaceholder } from '../components/analytics/GraphPlaceholder';
import { ExportButton } from '../components/analytics/ExportButton';

const DEMO_CLASSES = [
  { id: '1', name: 'Class 10-A' },
  { id: '2', name: 'Class 10-B' },
  { id: '3', name: 'Class 11-A' },
];

const getDefaultDateRange = () => {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
};

export function Analytics() {
  const [selectedClass, setSelectedClass] = useState('all');
  const [dateRange, setDateRange] = useState(getDefaultDateRange());
  const handleDateRangeChange = useCallback((start: string, end: string) => {
    setDateRange({ start, end });
  }, []);

  const handleExport = () => {
    const headers = ['Class', 'Date Range Start', 'Date Range End', 'Metric', 'Value'];
    const rows = [
      [selectedClass || 'all', dateRange.start, dateRange.end, 'Score Distribution', '—'],
      [selectedClass || 'all', dateRange.start, dateRange.end, 'Assignment Completion', '—'],
      [selectedClass || 'all', dateRange.start, dateRange.end, 'Student Engagement', '—'],
    ];
    const csvContent = [headers.join(','), ...rows.map((r) => r.map((c) => `"${c}"`).join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-${dateRange.start}-${dateRange.end}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main id="main-content" className="page-analytics" role="main">
      <div className="page-header">
        <h1 className="page-title">Analytics</h1>
        <ExportButton onClick={handleExport} />
      </div>

      <section className="analytics-section">
        <GlassCard>
          <AnalyticsFilters
            selectedClass={selectedClass}
            onClassChange={setSelectedClass}
            dateRange={dateRange}
            onDateRangeChange={handleDateRangeChange}
            classes={DEMO_CLASSES}
          />
        </GlassCard>
      </section>

      <section className="analytics-charts" aria-label="Analytics charts">
        <GraphPlaceholder title="Score Distribution by Topic" height={320} />
        <GraphPlaceholder title="Assignment Completion Over Time" height={280} />
        <GraphPlaceholder title="Student Engagement Trends" height={280} />
      </section>
    </main>
  );
}

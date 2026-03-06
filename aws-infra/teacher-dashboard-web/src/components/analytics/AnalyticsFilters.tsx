
interface AnalyticsFiltersProps {
  selectedClass: string;
  onClassChange: (classId: string) => void;
  dateRange: { start: string; end: string };
  onDateRangeChange: (start: string, end: string) => void;
  classes: { id: string; name: string }[];
}

export function AnalyticsFilters({
  selectedClass,
  onClassChange,
  dateRange,
  onDateRangeChange,
  classes,
}: AnalyticsFiltersProps) {
  return (
    <div className="analytics-filters" role="group" aria-label="Analytics filters">
      <label className="analytics-filters__label">
        Class
        <select
          value={selectedClass}
          onChange={(e) => onClassChange(e.target.value)}
          className="analytics-filters__select"
          aria-label="Select class"
        >
          <option value="all">All Classes</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label className="analytics-filters__label">
        Start date
        <input
          type="date"
          value={dateRange.start}
          onChange={(e) => onDateRangeChange(e.target.value, dateRange.end)}
          className="analytics-filters__input"
          aria-label="Start date"
        />
      </label>
      <label className="analytics-filters__label">
        End date
        <input
          type="date"
          value={dateRange.end}
          onChange={(e) => onDateRangeChange(dateRange.start, e.target.value)}
          className="analytics-filters__input"
          aria-label="End date"
        />
      </label>
    </div>
  );
}

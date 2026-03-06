interface StaleDataWarningProps {
  studentNames: string[];
  onDismiss?: () => void;
}

export function StaleDataWarning({ studentNames, onDismiss }: StaleDataWarningProps) {
  if (studentNames.length === 0) return null;

  return (
    <div
      className="stale-data-warning"
      role="alert"
      aria-live="polite"
    >
      <div className="stale-data-warning__content">
        <span className="stale-data-warning__icon" aria-hidden="true">
          ⏰
        </span>
        <div className="stale-data-warning__text">
          <h4 className="stale-data-warning__title">Stale Data Detected</h4>
          <p className="stale-data-warning__message">
            {studentNames.length === 1 ? (
              <>
                <strong>{studentNames[0]}</strong> hasn't synced in over 24 hours.
              </>
            ) : studentNames.length <= 3 ? (
              <>
                <strong>{studentNames.join(', ')}</strong> haven't synced in over 24 hours.
              </>
            ) : (
              <>
                <strong>{studentNames.length} students</strong> haven't synced in over 24 hours.
              </>
            )}
          </p>
        </div>
      </div>
      {onDismiss && (
        <button
          type="button"
          className="stale-data-warning__dismiss"
          onClick={onDismiss}
          aria-label="Dismiss warning"
        >
          ✕
        </button>
      )}
    </div>
  );
}

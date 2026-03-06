
interface ExportButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export function ExportButton({ onClick, disabled = false }: ExportButtonProps) {
  return (
    <button
      type="button"
      className="btn btn--secondary export-btn"
      onClick={onClick}
      disabled={disabled}
      aria-label="Export analytics data"
    >
      📥 Export
    </button>
  );
}

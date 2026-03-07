/**
 * Modal — glass overlay for confirmations / hardware warning (Thermal Vitreous).
 */

import { type ReactNode } from "react";

export interface ModalProps {
  open: boolean;
  onClose?: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="absolute inset-0 bg-deep/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        className="relative glass-panel rounded-2xl border border-glass-border shadow-glass max-w-md w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-glass-border">
          <h2 id="modal-title" className="text-lg font-semibold text-primary">
            {title}
          </h2>
        </div>
        <div className="p-6 text-primary/80 text-sm">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-glass-border flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

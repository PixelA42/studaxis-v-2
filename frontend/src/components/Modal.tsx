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
        className="relative content-card rounded-card border border-glass-border shadow-card max-w-md w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-glass-border">
          <h2 id="modal-title" className="text-lg font-extrabold font-anchor-bold text-heading-dark">
            {title}
          </h2>
        </div>
        <div className="p-6 text-heading-dark/80 text-sm font-medium">{children}</div>
        {footer && (
          <div className="px-6 py-4 border-t border-glass-border flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

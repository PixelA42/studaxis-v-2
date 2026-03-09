/**
 * Class Selector dropdown + Create Class button.
 * Lists all classes; changing selection updates activeClassId.
 * Create Class opens a modal to add a new class and displays the generated code.
 */

import { useState, useRef, useEffect } from 'react';
import { Icon } from '../icons/Icon';
import { useClass } from '../../context/ClassContext';
import { useTeacher } from '../../context/TeacherContext';
import { createClass } from '../../lib/teacherApi';
import type { ActiveClass, LegacyClass } from '../../context/ClassContext';

function isLegacy(c: ActiveClass): c is LegacyClass {
  return 'isLegacy' in c && c.isLegacy;
}

export function ClassSelector() {
  const { classes, activeClass, activeClassId, setActiveClassId, refreshClasses, isLoading } = useClass();
  const { teacher } = useTeacher();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState('');
  const [createdCode, setCreatedCode] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const allOptions: ActiveClass[] = [];
  if (classes.length > 0) {
    allOptions.push(...classes);
  } else if (teacher?.classCode) {
    allOptions.push({
      class_id: teacher.classCode,
      class_code: teacher.classCode,
      class_name: teacher.className || teacher.classCode,
      isLegacy: true,
    });
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const name = createName.trim();
    if (!name) {
      setCreateError('Enter a class name');
      return;
    }
    const teacherId = teacher?.teacherId || teacher?.classCode;
    if (!teacherId) {
      setCreateError('Not logged in');
      return;
    }
    setCreateLoading(true);
    setCreateError('');
    setCreatedCode(null);
    try {
      const cls = await createClass(teacherId, name);
      await refreshClasses();
      setCreatedCode(cls.class_code);
      setCreateName('');
      setActiveClassId(cls.class_id);
      setDropdownOpen(false);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create class');
    } finally {
      setCreateLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setCreateName('');
    setCreateError('');
    setCreatedCode(null);
  };

  const displayLabel = activeClass
    ? `${activeClass.class_name} (${activeClass.class_code})`
    : isLoading
      ? 'Loading…'
      : 'Select class';

  return (
    <div className="class-selector-wrap" ref={dropdownRef} style={{ position: 'relative' }}>
      <div className="dashboard-header-class-row" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="class-selector-dropdown" style={{ position: 'relative' }}>
          <button
            type="button"
            className="btn btn-ghost class-selector-btn"
            onClick={() => setDropdownOpen((o) => !o)}
            disabled={isLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 12px',
              borderRadius: 10,
              border: '1px solid var(--sd-border-subtle)',
              background: 'var(--sd-bg-glass)',
              fontSize: 13,
              minWidth: 180,
              justifyContent: 'space-between',
            }}
          >
            <span className="class-selector-label" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {displayLabel}
            </span>
            <Icon name={dropdownOpen ? 'arrow_up' : 'arrow_down'} size={14} color="var(--sd-grey)" />
          </button>
          {dropdownOpen && (
            <div
              className="class-selector-menu"
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                marginTop: 4,
                minWidth: 220,
                maxHeight: 280,
                overflowY: 'auto',
                background: 'var(--sd-bg-glass)',
                border: '1.5px solid var(--sd-border-subtle)',
                borderRadius: 12,
                boxShadow: 'var(--sd-shadow-card)',
                zIndex: 60,
              }}
            >
              {allOptions.map((c) => (
                <button
                  key={c.class_id}
                  type="button"
                  className="class-selector-option"
                  onClick={() => {
                    setActiveClassId(c.class_id);
                    setDropdownOpen(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '10px 14px',
                    textAlign: 'left',
                    border: 'none',
                    background: activeClassId === c.class_id ? 'var(--sd-accent-subtle)' : 'transparent',
                    color: 'var(--sd-dark)',
                    fontSize: 13,
                    cursor: 'pointer',
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{c.class_name}</span>
                  <span style={{ color: 'var(--sd-grey)', marginLeft: 6 }}>({c.class_code})</span>
                  {isLegacy(c) && (
                    <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--sd-grey)' }}>legacy</span>
                  )}
                </button>
              ))}
              {allOptions.length === 0 && !isLoading && (
                <div style={{ padding: 14, color: 'var(--sd-grey)', fontSize: 13 }}>
                  No classes yet. Create one below.
                </div>
              )}
            </div>
          )}
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => setModalOpen(true)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 12px',
            fontSize: 13,
          }}
        >
          <Icon name="plus" size={14} />
          Create Class
        </button>
      </div>

      {/* Create Class Modal */}
      {modalOpen && (
        <div
          className="modal-backdrop"
          onClick={closeModal}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.4)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <div
            className="create-class-modal"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--sd-bg)',
              borderRadius: 16,
              padding: 24,
              maxWidth: 400,
              width: '90%',
              boxShadow: 'var(--sd-shadow-card)',
            }}
          >
            <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>{createdCode ? 'Class Created' : 'Create New Class'}</h3>
            {createdCode ? (
              <div>
                <p style={{ marginBottom: 12, color: 'var(--sd-grey)' }}>
                  Share this code with students so they can join:
                </p>
                <div
                  style={{
                    padding: 14,
                    background: 'var(--sd-accent-subtle)',
                    borderRadius: 10,
                    fontFamily: 'monospace',
                    fontSize: 20,
                    fontWeight: 600,
                    letterSpacing: 2,
                    textAlign: 'center',
                  }}
                >
                  {createdCode}
                </div>
                <button type="button" className="btn btn-primary" onClick={closeModal} style={{ marginTop: 16, width: '100%' }}>
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreate}>
                <label className="label" style={{ display: 'block', marginBottom: 6 }}>Class Name</label>
                <input
                  className="input"
                  placeholder="e.g. Physics 11A, Math Section B"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  disabled={createLoading}
                  autoFocus
                  style={{ width: '100%', marginBottom: 12 }}
                />
                {createError && (
                  <div className="notif-banner notif-error" style={{ marginBottom: 12 }}>{createError}</div>
                )}
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button type="button" className="btn btn-ghost" onClick={closeModal}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={createLoading}>
                    {createLoading ? <span className="loading loading-spinner loading-sm" /> : 'Create'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

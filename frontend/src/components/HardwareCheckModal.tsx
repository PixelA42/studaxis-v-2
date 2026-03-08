/**
 * Hardware check warning modal — boot-time modal for Studaxis.
 * Mock checks: RAM (pass ≥4GB), CPU cores (pass ≥2), storage (pass ≥2GB free).
 * Sequential animation with progress bar. Green tick / orange warning / red fail per item.
 * Colors: #FA5C5C #FD8A6B #FEC288 #FBEF76 #00a8e8
 * Reference: hardware-check-warning-modal plan.
 */

import { useEffect, useState } from "react";

const COLORS = {
  red: "#FA5C5C",
  coral: "#FD8A6B",
  peach: "#FEC288",
  yellow: "#FBEF76",
  blue: "#00a8e8",
} as const;

type CheckStatus = "pass" | "warn" | "fail";

interface CheckResult {
  id: string;
  label: string;
  value: string;
  status: CheckStatus;
  threshold: string;
}

const CHECK_DELAY_MS = 600;

/** Mock hardware values for demo/fallback when API unavailable */
function mockHardware(): { ramGb: number; cpuCores: number; diskFreeGb: number } {
  return {
    ramGb: 5.2,
    cpuCores: 4,
    diskFreeGb: 12.1,
  };
}

function evaluateChecks(specs: { ramGb: number; cpuCores: number; diskFreeGb: number }): CheckResult[] {
  const minRam = 4;
  const minCpu = 2;
  const minDisk = 2;
  const ramWarn = specs.ramGb >= minRam && specs.ramGb < 6;
  const ramFail = specs.ramGb < minRam;
  const cpuFail = specs.cpuCores < minCpu;
  const diskFail = specs.diskFreeGb < minDisk;

  return [
    {
      id: "ram",
      label: "RAM",
      value: `${specs.ramGb.toFixed(1)} GB`,
      status: ramFail ? "fail" : ramWarn ? "warn" : "pass",
      threshold: `min ${minRam} GB`,
    },
    {
      id: "cpu",
      label: "CPU cores",
      value: `${specs.cpuCores}`,
      status: cpuFail ? "fail" : "pass",
      threshold: `min ${minCpu}`,
    },
    {
      id: "storage",
      label: "Storage (free)",
      value: `${specs.diskFreeGb.toFixed(1)} GB`,
      status: diskFail ? "fail" : "pass",
      threshold: `min ${minDisk} GB`,
    },
  ];
}

function StatusIcon({ status }: { status: CheckStatus }) {
  const styles = {
    pass: { color: "#22c55e" },
    warn: { color: COLORS.coral },
    fail: { color: COLORS.red },
  };
  const s = styles[status];

  if (status === "pass") {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={s}>
        <path d="M20 6L9 17l-5-5" />
      </svg>
    );
  }
  if (status === "warn") {
    return (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={s}>
        <path d="M12 9v4M12 17h.01" />
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      </svg>
    );
  }
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={s}>
      <circle cx="12" cy="12" r="10" />
      <path d="M15 9l-6 6M9 9l6 6" />
    </svg>
  );
}

export interface HardwareCheckModalProps {
  onContinue: () => void;
  /** Optional: use real API result when available; falls back to mock */
  specs?: { ram_gb?: number; cpu_count?: number; disk_free_gb?: number } | null;
}

const LEARN_MORE_URL = "https://github.com/PixelA42/studaxis-v-2#readme";

export function HardwareCheckModal({ onContinue, specs: apiSpecs }: HardwareCheckModalProps) {
  const [visibleCount, setVisibleCount] = useState(0);
  const [checks, setChecks] = useState<CheckResult[]>([]);
  const [progress, setProgress] = useState(0);

  const specs = apiSpecs
    ? {
        ramGb: apiSpecs.ram_gb ?? mockHardware().ramGb,
        cpuCores: apiSpecs.cpu_count ?? mockHardware().cpuCores,
        diskFreeGb: apiSpecs.disk_free_gb ?? mockHardware().diskFreeGb,
      }
    : mockHardware();

  const ramGb = specs.ramGb;
  const modelBadge = ramGb < 6 ? "llama3.2:3b-instruct-q2_K (~1.1GB)" : "llama3.2:3b-instruct-q4_K_M";

  useEffect(() => {
    setChecks(evaluateChecks(specs));
  }, [specs.ramGb, specs.cpuCores, specs.diskFreeGb]);

  useEffect(() => {
    const total = checks.length;
    if (total === 0) return;

    let idx = 0;
    const advance = () => {
      idx += 1;
      setVisibleCount(idx);
      setProgress((idx / total) * 100);
      if (idx < total) {
        setTimeout(advance, CHECK_DELAY_MS);
      }
    };
    const t = setTimeout(advance, CHECK_DELAY_MS);
    return () => clearTimeout(t);
  }, [checks.length]);

  return (
    <div
      className="relative overflow-hidden rounded-2xl p-6"
      style={{
        background: "rgba(255,255,255,0.85)",
        backdropFilter: "blur(16px)",
        border: "1px solid rgba(226,232,240,0.9)",
        boxShadow: "0 18px 45px rgba(15,23,42,0.08)",
      }}
    >
      {/* Gradient accent */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full opacity-60 blur-3xl -translate-y-1/2 pointer-events-none"
        style={{
          background: `radial-gradient(circle, ${COLORS.red}, ${COLORS.coral}, ${COLORS.peach}, transparent)`,
        }}
        aria-hidden
      />

      <div className="relative">
        <h2
          className="text-xl font-semibold mb-1"
          style={{ color: "#0F172A" }}
        >
          Checking your laptop
        </h2>
        <p className="text-sm mb-4" style={{ color: "#64748B" }}>
          Studaxis needs minimal hardware to run the AI tutor offline.
        </p>

        {/* Progress bar */}
        <div
          className="h-1.5 rounded-full mb-6 overflow-hidden"
          style={{ background: "rgba(226,232,240,0.8)" }}
        >
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${COLORS.red}, ${COLORS.coral}, ${COLORS.peach}, ${COLORS.yellow}, ${COLORS.blue})`,
            }}
          />
        </div>

        {/* Checks */}
        <div className="space-y-3">
          {checks.map((c, i) => (
            <div
              key={c.id}
              className="flex items-center gap-3 p-3 rounded-xl transition-all duration-500 ease-out"
              style={{
                opacity: i < visibleCount ? 1 : 0.3,
                transform: i < visibleCount ? "translateX(0)" : "translateX(-8px)",
                background: i < visibleCount ? "rgba(248,250,252,0.6)" : "transparent",
              }}
            >
              <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-white/80 border">
                <StatusIcon status={c.status} />
              </div>
              <div className="flex-1 min-w-0">
                <span className="font-medium" style={{ color: "#0F172A" }}>{c.label}</span>
                <span className="text-sm ml-2" style={{ color: "#64748B" }}>
                  {c.value} / {c.threshold}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Model badge */}
        <div
          className="mt-4 px-3 py-2 rounded-lg text-xs font-mono"
          style={{
            background: "rgba(0,168,232,0.08)",
            border: "1px solid rgba(0,168,232,0.2)",
            color: COLORS.blue,
          }}
        >
          Using {modelBadge}
        </div>

        {/* Buttons */}
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:gap-3">
          <button
            type="button"
            onClick={onContinue}
            className="flex-1 px-5 py-2.5 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
            style={{ background: COLORS.blue }}
          >
            Continue Anyway
          </button>
          <a
            href={LEARN_MORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 px-5 py-2.5 rounded-xl font-medium text-center transition-colors border"
            style={{
              borderColor: "rgba(226,232,240,0.9)",
              color: "#64748B",
            }}
          >
            Learn More
          </a>
        </div>
      </div>
    </div>
  );
}

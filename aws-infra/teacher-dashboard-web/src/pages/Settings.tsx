import { GlassCard } from '../components/dashboard/GlassCard';
import { useTheme } from '../context/ThemeContext';

export function Settings() {
  const { theme, toggleTheme } = useTheme();

  return (
    <main id="main-content" className="page-settings" role="main">
      <h1 className="page-title">Settings</h1>

      <GlassCard>
        <h2 className="card-title">Appearance</h2>
        <p className="card-sub">Theme and display preferences</p>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={toggleTheme}
          aria-pressed={theme === 'dark'}
        >
          {theme === 'light' ? '🌙 Dark mode' : '☀️ Light mode'}
        </button>
      </GlassCard>

      <GlassCard>
        <h2 className="card-title">Account</h2>
        <p className="card-sub">Profile and security — integration pending</p>
      </GlassCard>
    </main>
  );
}

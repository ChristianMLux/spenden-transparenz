/**
 * Runs before first paint so a stored choice does not flash the other theme. It is the
 * only inline script in the application. Kept deliberately tiny and dependency-free.
 */
const SCRIPT = `try{var c=localStorage.getItem('spenden-theme')||'system';var d=c==='dark'||(c==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.add(d?'dark':'light')}catch(e){}`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: SCRIPT }} />;
}

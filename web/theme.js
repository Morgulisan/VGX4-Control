// Runs before first paint so a forced light/dark theme never flashes the system theme.
try {
  const theme=JSON.parse(localStorage.getItem('vgx4.preferences.v1')||'{}').theme;
  if(theme==='light'||theme==='dark') document.documentElement.dataset.theme=theme;
} catch (_) { /* Without storage the page follows the system theme. */ }

/**
 * Main map page: shows filter panel + map + news list side-by-side.
 * Filter state is synced with URL query params (see §9 frontend rules).
 */
export default function MapPage() {
  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "1rem", borderBottom: "1px solid #ddd" }}>
        <h1>Geo News Scraper</h1>
      </header>
      <main style={{ flex: 1, display: "flex" }}>
        {/* FilterPanel, MapView, NewsList components will be placed here */}
        <p style={{ margin: "auto" }}>Map &amp; filters coming soon…</p>
      </main>
    </div>
  );
}

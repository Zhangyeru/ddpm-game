export function LoadingRoundShell() {
  return (
    <main className="console-grid console-grid--loading" aria-busy="true">
      <section className="panel side-panel skeleton-panel">
        <div className="skeleton skeleton--title" />
        <div className="skeleton skeleton--card" />
        <div className="skeleton skeleton--card" />
        <div className="skeleton skeleton--card" />
      </section>

      <section className="panel canvas-panel skeleton-panel">
        <div className="skeleton skeleton--title" />
        <div className="skeleton skeleton--canvas" />
        <div className="skeleton skeleton--bar" />
        <div className="skeleton-grid skeleton-grid--double">
          <div className="skeleton skeleton--chip" />
          <div className="skeleton skeleton--chip" />
          <div className="skeleton skeleton--chip" />
          <div className="skeleton skeleton--chip" />
        </div>
      </section>

      <section className="console-stack console-stack--right">
        <section className="panel side-panel skeleton-panel">
          <div className="skeleton skeleton--title" />
          <div className="skeleton skeleton--card" />
          <div className="skeleton skeleton--card" />
          <div className="skeleton skeleton--card" />
        </section>

        <section className="panel guess-panel skeleton-panel">
          <div className="skeleton skeleton--title" />
          <div className="skeleton-grid skeleton-grid--double">
            <div className="skeleton skeleton--chip" />
            <div className="skeleton skeleton--chip" />
            <div className="skeleton skeleton--chip" />
            <div className="skeleton skeleton--chip" />
          </div>
          <div className="skeleton skeleton--button" />
        </section>
      </section>
    </main>
  );
}

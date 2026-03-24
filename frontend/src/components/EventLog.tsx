type EventLogProps = {
  events: string[];
};

export function EventLog({ events }: EventLogProps) {
  const visibleEvents = [...events].reverse().slice(0, 5);

  return (
    <section className="panel side-panel event-log-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">信号记录</p>
          <h2>事件日志</h2>
        </div>
        <span className="tool-counter">最近 5 条</span>
      </div>

      <ul className="event-log">
        {visibleEvents.length === 0 ? (
          <li className="event-log__empty">
            正在等待遥测数据。
          </li>
        ) : (
          visibleEvents.map((entry, index) => (
            <li className="event-log__entry" key={`${entry}-${index}`}>
              {entry}
            </li>
          ))
        )}
      </ul>
    </section>
  );
}

type EventLogProps = {
  events: string[];
};

export function EventLog({ events }: EventLogProps) {
  return (
    <section className="panel side-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">信号记录</p>
          <h2>事件日志</h2>
        </div>
      </div>

      <ul className="event-log">
        {events.length === 0 ? (
          <li className="event-log__empty">
            正在等待遥测数据。
          </li>
        ) : (
          [...events].reverse().map((entry, index) => (
            <li className="event-log__entry" key={`${entry}-${index}`}>
              {entry}
            </li>
          ))
        )}
      </ul>
    </section>
  );
}

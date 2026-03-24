type InlineErrorProps = {
  detail?: string;
  onDismiss?: () => void;
  onRetry?: () => void;
  title: string;
};

export function InlineError({
  detail,
  onDismiss,
  onRetry,
  title
}: InlineErrorProps) {
  return (
    <section className="inline-error" role="alert">
      <div>
        <p className="eyebrow">可恢复错误</p>
        <strong className="inline-error__title">{title}</strong>
        {detail ? <p className="inline-error__detail">{detail}</p> : null}
      </div>
      <div className="inline-error__actions">
        {onRetry ? (
          <button className="action-button" onClick={onRetry} type="button">
            重试
          </button>
        ) : null}
        {onDismiss ? (
          <button className="secondary-button" onClick={onDismiss} type="button">
            关闭提示
          </button>
        ) : null}
      </div>
    </section>
  );
}

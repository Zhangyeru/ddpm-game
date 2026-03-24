import type { ReactNode } from "react";

type EmptyStateProps = {
  action?: ReactNode;
  detail: string;
  eyebrow?: string;
  title: string;
};

export function EmptyState({
  action,
  detail,
  eyebrow,
  title
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <strong className="empty-state__title">{title}</strong>
      <p className="empty-state__detail">{detail}</p>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}

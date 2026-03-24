import { useEffect } from "react";
import type { ReactNode } from "react";

type DrawerProps = {
  children: ReactNode;
  onClose: () => void;
  open: boolean;
  title: string;
};

export function Drawer({ children, onClose, open, title }: DrawerProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="drawer-root" role="dialog" aria-modal="true" aria-label={title}>
      <button
        aria-label="关闭侧边面板"
        className="drawer-backdrop"
        onClick={onClose}
        type="button"
      />
      <section className="drawer-panel">
        <header className="drawer-header">
          <div>
            <p className="eyebrow">本地记录</p>
            <h2>{title}</h2>
          </div>
          <button className="secondary-button" onClick={onClose} type="button">
            关闭
          </button>
        </header>
        <div className="drawer-content">{children}</div>
      </section>
    </div>
  );
}

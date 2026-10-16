import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

export function Button({ variant = "secondary", busy = false, className = "", disabled, children, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; busy?: boolean }) {
  const classes = ["ui-button", `ui-button--${variant}`, className].filter(Boolean).join(" ");
  return <button className={classes} aria-busy={busy || undefined} disabled={disabled || busy} {...props}>{children}</button>;
}

type SurfaceTone = "default" | "subtle" | "emphasis";

export function Surface({ tone = "default", className = "", children, ...props }: HTMLAttributes<HTMLDivElement> & { tone?: SurfaceTone }) {
  const classes = ["ui-surface", `ui-surface--${tone}`, className].filter(Boolean).join(" ");
  return <div className={classes} {...props}>{children}</div>;
}

type NoticeTone = "neutral" | "info" | "success" | "warning" | "danger";
type BadgeTone = NoticeTone | "accent";

export function StatusNotice({ tone = "neutral", title, role, action, children, className = "" }: {
  tone?: NoticeTone;
  title?: ReactNode;
  role?: "status" | "alert";
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return <div className={["status-notice", `status-notice--${tone}`, className].filter(Boolean).join(" ")} role={role}>
    <div>{title && <strong className="status-notice__title">{title}</strong>}<div className="status-notice__body">{children}</div></div>
    {action && <div className="status-notice__action">{action}</div>}
  </div>;
}

export function Badge({ tone = "neutral", children, className = "", ...props }: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return <span className={["ui-badge", `ui-badge--${tone}`, className].filter(Boolean).join(" ")} {...props}>{children}</span>;
}

export function SectionHeader({ eyebrow, title, description, action, className = "" }: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return <header className={["section-header", className].filter(Boolean).join(" ")}>
    <div>{eyebrow && <p className="section-header__eyebrow">{eyebrow}</p>}<h2>{title}</h2>{description && <p className="section-header__description">{description}</p>}</div>
    {action && <div className="section-header__action">{action}</div>}
  </header>;
}

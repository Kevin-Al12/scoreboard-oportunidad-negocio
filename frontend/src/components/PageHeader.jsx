import { Search } from "lucide-react";
import NotificacionesBell from "./NotificacionesBell";

export default function PageHeader({ eyebrow, title, pills, search, primaryAction, extra }) {
  return (
    <header className="ph">
      <div className="ph-titles">
        {eyebrow && <div className="ph-eyebrow">{eyebrow}</div>}
        <h1 className="ph-title">{title}</h1>
      </div>

      {pills && pills.length > 0 && (
        <div className="ph-pills">
          {pills.map((p) => (
            <button key={p.label} className={`ph-pill${p.active ? " active" : ""}`} onClick={p.onClick}>
              {p.label}
            </button>
          ))}
        </div>
      )}

      {search && (
        <label className="ph-search">
          <Search size={17} strokeWidth={2} />
          <input
            type="search"
            placeholder={search.placeholder || "Buscar…"}
            value={search.value}
            onChange={(e) => search.onChange(e.target.value)}
          />
          <span className="ph-kbd">⌘K</span>
        </label>
      )}

      {primaryAction &&
        (primaryAction.href ? (
          <a href={primaryAction.href} target="_blank" rel="noreferrer" className="btn" style={{ textDecoration: "none" }}>
            {primaryAction.icon && <primaryAction.icon size={16} strokeWidth={2.3} />}
            {primaryAction.label}
          </a>
        ) : (
          <button type="button" onClick={primaryAction.onClick} className="btn">
            {primaryAction.icon && <primaryAction.icon size={16} strokeWidth={2.3} />}
            {primaryAction.label}
          </button>
        ))}

      {extra}
      <NotificacionesBell />
    </header>
  );
}

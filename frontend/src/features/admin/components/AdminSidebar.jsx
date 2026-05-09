const AdminSidebar = ({ items, activeView, onSelect }) => (
  <aside className="shrink-0 border-b border-neutral-200 bg-white lg:w-64 lg:border-b-0 lg:border-r">
    <nav className="flex gap-2 overflow-x-auto px-4 py-3 lg:flex-col lg:px-3 lg:py-6" aria-label="Admin dashboard sections">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = item.id === activeView;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item.id)}
            className={`flex min-w-max items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-semibold transition-colors ${
              isActive
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-950'
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {item.label}
          </button>
        );
      })}
    </nav>
  </aside>
);

export default AdminSidebar;

export function InfoRuta({ label, varde }: { label: string; varde: string | number }) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-lg p-4 text-center transition-all hover:border-gray-200 hover:shadow-sm">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-lg font-semibold text-gray-900">{varde}</p>
    </div>
  );
}

export function Sektion({
  titel,
  children,
  badge,
}: {
  titel: string;
  children: React.ReactNode;
  badge?: string;
}) {
  return (
    <div className="mb-12">
      <div className="flex items-center gap-2 mb-5">
        <h2 className="text-xl font-bold text-gray-900 border-l-4 border-red-600 pl-3">
          {titel}
        </h2>
        {badge && (
          <span className="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5">
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

export function BockRad({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-3 text-gray-700">
      <span className="shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-red-100 text-red-600">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} className="w-3 h-3">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </span>
      {text}
    </li>
  );
}

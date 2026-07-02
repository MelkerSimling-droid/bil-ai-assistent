export default function Header() {
  return (
    <header className="border-b border-gray-200 sticky top-0 bg-white z-10">
      <div className="border-t-4 border-red-600" />
      <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/toyota-logo.jpg" alt="Toyota Simling Bil" className="h-10 w-auto" />
        </div>
        <nav className="hidden md:flex gap-6 text-sm text-gray-700 font-medium">
          <span className="hover:text-red-600 cursor-pointer transition-colors">Bilar</span>
          <span className="hover:text-red-600 cursor-pointer transition-colors">Service & verkstad</span>
          <span className="hover:text-red-600 cursor-pointer transition-colors">Finansiering</span>
          <span className="hover:text-red-600 cursor-pointer transition-colors">Kontakt</span>
        </nav>
      </div>
    </header>
  );
}
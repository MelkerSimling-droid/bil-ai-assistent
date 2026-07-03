export default function LoadingState({ text = "Laddar..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-400">
      <div className="h-8 w-8 rounded-full border-2 border-gray-200 border-t-red-600 animate-spin" />
      <p className="text-sm">{text}</p>
    </div>
  );
}

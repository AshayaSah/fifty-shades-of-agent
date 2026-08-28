import Chat from "./components/Chat";

export default function Home() {
  return (
    <main className="flex-1 flex flex-col h-full">
      <header className="border-b border-zinc-800 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <h1 className="text-lg font-semibold">TrueForge Assistant</h1>
          <span className="text-xs text-zinc-500">Powered by TrueForge</span>
        </div>
      </header>
      <div className="flex-1 flex flex-col min-h-0">
        <Chat />
      </div>
    </main>
  );
}
